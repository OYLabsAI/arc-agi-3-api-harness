from __future__ import annotations

import json
import sqlite3
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path

from .perception import image_bytes


def write_json(path: Path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(path)


class Store:
    """Run-local evidence. No memory is imported from other games or previous attempts."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=False)
        self.directory = directory
        self.db = sqlite3.connect(directory / "evidence.sqlite")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, payload TEXT);
            CREATE TABLE memories (key TEXT PRIMARY KEY, payload TEXT);
        """)
        self.log = (directory / "events.jsonl").open("a", encoding="utf-8", buffering=1)
        self.transitions = []
        self.observations = []

    def event(self, kind, data):
        row = {"at": datetime.now(UTC).isoformat(), "kind": kind, "data": data}
        payload = json.dumps(row)
        self.db.execute("INSERT INTO events(kind,payload) VALUES (?,?)", (kind, payload))
        self.db.commit()
        self.log.write(payload + "\n")
        if kind == "provider_model_call":
            with (self.directory / "model-calls.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(data) + "\n")
        elif kind in ("provider_error", "provider_recovery"):
            with (self.directory / "provider-recovery.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(payload + "\n")

    def observation(self, obs):
        index = len(self.observations)
        self.observations.append(obs)
        self.event("observation", {"index": index, **obs.payload()})
        (self.directory / "current.png").write_bytes(image_bytes(obs.grid))
        write_json(self.directory / "current.json", {"index": index, **obs.payload()})
        return index

    def transition(self, before, action, after, experiment, prediction, delta):
        item = {
            "index": len(self.transitions),
            "before": before.fingerprint,
            "after": after.fingerprint,
            "action": action.command(),
            "experiment": experiment,
            "prediction": prediction,
            "delta": delta,
            "state": after.state,
            "levels_completed": after.levels_completed,
        }
        self.transitions.append(item)
        self.event("transition", item)
        return item

    def remember(self, note):
        if note.confidence == "supported" and not note.evidence:
            raise ValueError("Supported claims need observed transition indices")
        if any(i < 0 or i >= len(self.transitions) for i in note.evidence):
            raise ValueError("Memory references a transition that has not occurred")
        payload = note.model_dump()
        self.db.execute(
            "INSERT OR REPLACE INTO memories(key,payload) VALUES (?,?)", (note.key, json.dumps(payload))
        )
        self.db.commit()
        self.event("memory", payload)
        return payload

    def memories(self):
        return [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM memories ORDER BY key")]

    def history(self, query="", limit=8):
        query = query.casefold()
        return {
            "transitions": [t for t in self.transitions if query in json.dumps(t).casefold()][-limit:],
            "memories": [m for m in self.memories() if query in json.dumps(m).casefold()][-limit:],
        }

    def path(self, source, target):
        # Contradictory observations invalidate an edge instead of choosing the favorable outcome.
        outcomes = defaultdict(set)
        for t in self.transitions:
            outcomes[(t["before"], json.dumps(t["action"], sort_keys=True))].add(t["after"])
        graph = defaultdict(list)
        for (start, command), ends in outcomes.items():
            if len(ends) == 1 and json.loads(command)["name"] != "RESET":
                graph[start].append((next(iter(ends)), json.loads(command)))
        seen, queue = {source}, deque([(source, [])])
        while queue:
            state, path = queue.popleft()
            if state == target:
                return {
                    "found": True,
                    "actions": path,
                    "caveat": "An empirical path through observed frames, not proof of hidden-state equivalence.",
                }
            for end, command in graph[state]:
                if end not in seen:
                    seen.add(end)
                    queue.append((end, path + [command]))
        return {"found": False, "actions": []}

    def close(self):
        self.log.close()
        self.db.close()
