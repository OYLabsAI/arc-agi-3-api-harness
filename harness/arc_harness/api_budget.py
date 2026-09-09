"""Persistent, run-wide reservations. Amounts are integer micro-USD, never invoices."""

from __future__ import annotations

import json
import math
import sqlite3
import time
from datetime import UTC, datetime


class BudgetStop(RuntimeError):
    pass


# GPT-6 Astra published rates checked 2026-09-08. Reserve at the higher
# long-context rates, including the most expensive input category (cache writes).
INPUT_RESERVE_PER_TOKEN = 25
OUTPUT_RESERVE_PER_TOKEN = 75
MAX_CONTEXT = 1_050_000
MAX_INPUT = 922_000
MAX_OUTPUT = 128_000


def usage_cost(usage):
    """Return (estimate, conservative charge); cached/reasoning tokens are subsets."""
    if not isinstance(usage, dict):
        raise ValueError("Usage missing")
    i, o = usage.get("input_tokens"), usage.get("output_tokens")
    if any(type(x) is not int or x < 0 for x in (i, o)):
        raise ValueError("Invalid usage")
    if usage.get("total_tokens") != i + o:
        raise ValueError("Usage total does not reconcile")
    details = usage.get("input_tokens_details") or {}
    cached, writes = details.get("cached_tokens"), details.get("cache_write_tokens")
    reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
    if reasoning is not None and (type(reasoning) is not int or not 0 <= reasoning <= o):
        raise ValueError("Invalid reasoning subset")
    if cached is not None and (type(cached) is not int or not 0 <= cached <= i):
        raise ValueError("Invalid cached subset")
    if writes is not None and (type(writes) is not int or not 0 <= writes <= i - (cached or 0)):
        raise ValueError("Invalid cache-write subset")
    # Integer half-microdollars accommodate the 12.50 rate without float rounding.
    factor, output_rate = (2, 75) if i > 272_000 else (1, 50)
    if cached is None or writes is None:
        estimate = None
        upper = math.ceil(i * 12.5 * factor) + o * output_rate
    else:
        upper = ((i - cached - writes) * 20 + cached * 2 + writes * 25) * factor
        upper = (upper + 1) // 2 + o * output_rate
        estimate = upper
    return estimate, upper


class Ledger:
    """One SQLite transaction precedes every paid request; never resume a run."""

    def __init__(self, path, *, approved_usd, max_requests, max_seconds, cleanup_seconds=180,
                 started=None, clock=time.monotonic):
        from decimal import Decimal

        cap = Decimal(str(approved_usd)) * 1_000_000
        if not cap.is_finite() or cap <= 0 or cap != cap.to_integral_value():
            raise ValueError("A finite positive USD cap with at most 6 decimals is required")
        if type(max_requests) is not int or max_requests <= 0:
            raise ValueError("Positive integer request limit required")
        if not math.isfinite(max_seconds) or not 0 <= cleanup_seconds < max_seconds:
            raise ValueError("Invalid global deadline")
        self.cap, self.max_requests = int(cap), max_requests
        self.clock = clock
        self.started = clock() if started is None else started
        self.deadline = self.started + max_seconds
        self.work_deadline = self.deadline - cleanup_seconds
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE requests (id INTEGER PRIMARY KEY, kind TEXT, "
                        "reserved INTEGER, charge INTEGER, status TEXT, detail TEXT)")
        self.db.execute("CREATE TABLE input_counts (id INTEGER PRIMARY KEY, status TEXT, detail TEXT)")

    def check_dispatch(self):
        self.check_time()
        rows = self.db.execute("SELECT status FROM requests UNION ALL SELECT status FROM input_counts").fetchall()
        if any(status not in ("accounted", "recorded") for (status,) in rows):
            raise BudgetStop("unresolved_request_charge")
        if len(rows) >= self.max_requests:
            raise BudgetStop("global_request_limit")

    def begin_count(self, metadata):
        """Journal dispatch, without inventing a price for the counting endpoint."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.check_dispatch()
            detail = {**metadata, "started_at": datetime.now(UTC).isoformat(),
                      "billing_status": "NOT SATISFIED: counting endpoint price not established",
                      "charge_micro_usd": None}
            cursor = self.db.execute("INSERT INTO input_counts(status,detail) VALUES('pending',?)",
                                     (json.dumps(detail),))
            self.db.execute("COMMIT")
            return cursor.lastrowid
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def finish_count(self, count_id, metadata, *, failed=False):
        row = self.db.execute("SELECT status,detail FROM input_counts WHERE id=?", (count_id,)).fetchone()
        if row is None or row[0] != "pending":
            raise ValueError("Input count is not pending")
        self.db.execute("UPDATE input_counts SET status=?,detail=? WHERE id=?",
                        ("uncertain" if failed else "recorded",
                         json.dumps({**json.loads(row[1]), **metadata}), count_id))

    def remaining_seconds(self):
        return max(0, self.work_deadline - self.clock())

    def check_time(self, required_seconds=0):
        if self.remaining_seconds() <= required_seconds:
            raise BudgetStop("global_deadline")

    def reserve(self, kind, input_bound, output_bound):
        self.check_time()
        if not 0 <= input_bound <= MAX_CONTEXT or not 1 <= output_bound <= MAX_OUTPUT:
            raise ValueError("Request bound exceeds the reviewed model limits")
        amount = input_bound * INPUT_RESERVE_PER_TOKEN + output_bound * OUTPUT_RESERVE_PER_TOKEN
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.check_dispatch()
            rows = self.db.execute("SELECT charge,status FROM requests").fetchall()
            if any(status in ("pending", "uncertain", "bound_violation") for _, status in rows):
                raise BudgetStop("unresolved_request_charge")
            if len(rows) >= self.max_requests:
                raise BudgetStop("global_request_limit")
            if sum(row[0] for row in rows) + amount > self.cap:
                raise BudgetStop("global_cost_reservation")
            cursor = self.db.execute("INSERT INTO requests(kind,reserved,charge,status,detail) "
                                     "VALUES(?,?,?,'pending',?)", (kind, amount, amount, json.dumps({
                                         "started_at": datetime.now(UTC).isoformat(),
                                         "input_bound": input_bound, "output_bound": output_bound,
                                     })))
            self.db.execute("COMMIT")
            return cursor.lastrowid
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def settle(self, request_id, usage, metadata):
        row = self.db.execute("SELECT reserved,status,detail FROM requests WHERE id=?",
                              (request_id,)).fetchone()
        if row is None or row[1] != "pending":
            raise ValueError("Reservation not pending")
        detail = {**json.loads(row[2]), **metadata, "usage": usage}
        try:
            estimate, charge = usage_cost(usage)
        except ValueError:
            self.uncertain(request_id, "missing_or_invalid_usage", metadata)
            raise BudgetStop("unresolved_request_usage") from None
        detail["estimated_micro_usd"] = estimate
        violation = (charge > row[0] or usage["input_tokens"] > detail["input_bound"]
                     or usage["output_tokens"] > detail["output_bound"])
        status = "bound_violation" if violation else "accounted"
        self.db.execute("UPDATE requests SET charge=?,status=?,detail=? WHERE id=?",
                        (max(charge, row[0]) if violation else charge, status, json.dumps(detail), request_id))
        if violation:
            raise BudgetStop("provider_exceeded_reserved_bound")

    def uncertain(self, request_id, reason, metadata=None):
        row = self.db.execute("SELECT status,detail FROM requests WHERE id=?", (request_id,)).fetchone()
        if row and row[0] == "pending":
            detail = {**json.loads(row[1]), **(metadata or {}), "error_type": reason}
            self.db.execute("UPDATE requests SET status='uncertain',detail=? WHERE id=?",
                            (json.dumps(detail), request_id))

    def report(self):
        rows = [{"id": i, "kind": k, "reservation_micro_usd": r, "charge_micro_usd": c,
                 "status": s, **json.loads(d)} for i, k, r, c, s, d in
                self.db.execute("SELECT * FROM requests ORDER BY id")]
        counts = [{"id": i, "status": s, **json.loads(d)} for i, s, d in
                  self.db.execute("SELECT * FROM input_counts ORDER BY id")]
        return {"approved_usd": self.cap / 1e6, "charged_or_reserved_usd":
                sum(x["charge_micro_usd"] for x in rows) / 1e6,
                "input_count_operations": counts, "dispatched_operations": len(rows) + len(counts),
                "max_operations": self.max_requests,
                "cost_coverage_complete": not counts,
                "cost_coverage_note": "Input-count charges remain unknown" if counts else None,
                "billed_usd": None, "billing_reconciliation": "pending_provider_invoice",
                "elapsed_seconds": self.clock() - self.started,
                "uncertain_requests": sum(x["status"] != "accounted" for x in rows), "requests": rows}

    def close(self):
        self.db.close()
