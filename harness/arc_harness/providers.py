from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

from .prompt import SYSTEM
from .types import ModelReply, ToolCall, tool_schemas


class ResponsesProvider:
    """Preserves full response items, including encrypted reasoning, between tool calls."""

    def __init__(self, model="gpt-6-astra", effort="high", client=None):
        from openai import OpenAI

        if client is None and not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("Set OPENAI_API_KEY, or select --provider codex to use your Codex login")
        self.client = client or OpenAI(max_retries=0)
        self.model, self.effort = model, effort
        self.items = []

    def next(self, context, image_path, timeout, token_allowance):
        # Keep reasoning items and tool-call/result pairing intact; no lossy sliding window.
        if image_path:
            import base64

            url = "data:image/png;base64," + base64.b64encode(Path(image_path).read_bytes()).decode()
            content = [
                {"type": "input_text", "text": json.dumps(context)},
                {"type": "input_image", "image_url": url, "detail": "original"},
            ]
        else:
            content = json.dumps(context)
        self.items.append({"role": "user", "content": content})
        response = self.client.with_options(timeout=timeout).responses.create(
            model=self.model,
            instructions=SYSTEM,
            reasoning={"effort": self.effort},
            input=self.items,
            tools=tool_schemas(),
            parallel_tool_calls=False,
            tool_choice="required",
            include=["reasoning.encrypted_content"],
            store=False,
            max_output_tokens=max(1, min(16000, token_allowance if token_allowance is not None else 16000)),
        )
        self.items.extend(item.model_dump(exclude_none=True) for item in response.output)
        if response.status != "completed":
            raise RuntimeError(f"Model response did not complete: {response.status}; no game action executed")
        calls = [
            ToolCall(i.name, json.loads(i.arguments), i.call_id)
            for i in response.output
            if i.type == "function_call"
        ]
        usage = response.usage
        return ModelReply(calls, usage.input_tokens if usage else 0, usage.output_tokens if usage else 0)

    def result(self, call, result):
        self.items.append(
            {"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)}
        )

    def close(self):
        pass


ENVELOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": [t["name"] for t in tool_schemas()]},
        "arguments_json": {
            "type": "string",
            "description": "JSON-encoded object of arguments for the selected tool",
        },
    },
    "required": ["tool", "arguments_json"],
    "additionalProperties": False,
}


def codex_executable():
    explicit = os.environ.get("CODEX_BIN")
    if explicit:
        return explicit
    # The bundled binary is often newer than a separately installed npm CLI on macOS.
    for path in (
        "/Applications/Codex.app/Contents/Resources/codex",
        "/Applications/ChatGPT.app/Contents/Resources/codex",
    ):
        if Path(path).is_file():
            return path
    binary = shutil.which("codex")
    if binary:
        return binary
    raise ValueError("Codex CLI not found. Set CODEX_BIN or use --provider openai")


class CodexProvider:
    """Development adapter using one dedicated Codex conversation per game.

    Built-in external tools are disabled. A temporary empty cwd keeps repository instructions
    and game files out of the input. This is a research adapter, not a contest sandbox.
    """

    def __init__(self, model="gpt-6-astra", effort="high"):
        self.model, self.effort = model, effort
        self.binary = codex_executable()
        self.temp = tempfile.TemporaryDirectory(prefix="arc-solver-")
        self.directory = Path(self.temp.name)
        self.schema = self.directory / "decision.schema.json"
        self.schema.write_text(json.dumps(ENVELOPE_SCHEMA))
        self.thread_id = None
        self.pending = []

    def command(self, image_path):
        args = [self.binary, "exec"]
        if self.thread_id:
            args += ["resume", self.thread_id]
        else:
            args += ["--sandbox", "read-only"]
        args += [
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--json",
            "--model",
            self.model,
            "--output-schema",
            str(self.schema),
            "-c",
            f'model_reasoning_effort="{self.effort}"',
            "-c",
            'approval_policy="never"',
            "-c",
            'web_search="disabled"',
            "-c",
            "project_doc_max_bytes=0",
        ]
        for feature in (
            "shell_tool",
            "unified_exec",
            "multi_agent",
            "apps",
            "plugins",
            "hooks",
            "browser_use",
            "computer_use",
            "image_generation",
            "memories",
            "view_image",
            "goals",
            "sleep_tool",
            "tool_suggest",
            "skill_search",
        ):
            args += ["--disable", feature]
        args += ["--enable", "skip_host_skill_discovery"]
        if image_path:
            args += ["--image", str(Path(image_path).resolve())]
        return args + ["-"]

    def next(self, context, image_path, timeout, token_allowance):
        prompt = {"observation": context, "tool_results": self.pending}
        if self.thread_id is None:
            prompt.update(
                {
                    "instructions": SYSTEM,
                    "response_format": "Return {tool, arguments_json}. Select exactly one of the following tools. Do not use Codex's built-in tools.",
                    "tools": tool_schemas(),
                }
            )
        # Do not inherit desktop thread identifiers or runtime connection variables.
        keep = (
            "HOME",
            "PATH",
            "USER",
            "LOGNAME",
            "TMPDIR",
            "CODEX_HOME",
            "LANG",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        )
        env = {key: os.environ[key] for key in keep if key in os.environ}
        process = subprocess.Popen(
            self.command(image_path),
            cwd=self.directory,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(json.dumps(prompt), timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        if process.returncode:
            raise RuntimeError(f"Codex exited {process.returncode}: {stderr[-2000:]}")
        final, usage, failure = None, {}, None
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "thread.started":
                self.thread_id = event["thread_id"]
            if event.get("type") == "turn.completed":
                usage = event.get("usage", {})
            if event.get("type") in ("turn.failed", "error"):
                failure = event
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    final = item.get("text")
                if item.get("type") in ("command_execution", "mcp_tool_call", "web_search", "file_change"):
                    raise RuntimeError("Unexpected external tool use by Codex: rejecting this evaluation")
        if failure or final is None:
            raise RuntimeError(f"Codex returned no valid decision: {failure or stderr[-1500:]}")
        answer = json.loads(final)
        arguments = json.loads(answer["arguments_json"])
        self.pending = []
        return ModelReply(
            [ToolCall(answer["tool"], arguments)], usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        )

    def result(self, call, result):
        self.pending.append({"tool": call.name, "result": result})

    def close(self):
        self.temp.cleanup()


class ScriptedProvider:
    """Deterministic integration testing only; never reported as benchmark intelligence."""

    model, effort = "scripted-test-fixture", "none"

    def __init__(self, calls):
        self.calls = iter(calls)
        self.results = []

    def next(self, context, image_path, timeout, token_allowance):
        return ModelReply([next(self.calls, ToolCall("stop", {"reason": "End of test script"}))])

    def result(self, call, result):
        self.results.append(result)

    def close(self):
        pass
