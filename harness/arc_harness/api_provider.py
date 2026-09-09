"""Explicit Responses API transport with complete opaque state and bounded requests."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import uuid
from pathlib import Path

import httpx
from openai import OpenAI

from .api_budget import MAX_INPUT, BudgetStop
from .deadline import wall_timeout
from .prompt import SYSTEM
from .types import ModelReply, ToolCall, tool_schemas

INSTRUCTIONS = SYSTEM + (
    "\nTool names have an arc_ prefix. Continue calling tools until WIN or an exhausted budget. "
    "Select one tool at a time and await its result. A tokens_left value of null means no cumulative token cutoff.\n"
)

# Responses compaction_trigger requires a cap of at least 20,000 tokens.
# Unlike the standalone compact endpoint, this is an explicit wire-level cap.
COMPACTION_OUTPUT_TOKENS = 20000


def schemas():
    return [{**t, "name": "arc_" + t["name"]} for t in tool_schemas()]


def api_client(key=None, *, transport=None):
    key = key or os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENAI_API_KEY is required; subscription fallback is disabled")
    # Ignore endpoint/proxy/project overrides and never load an auth file or .env.
    return OpenAI(api_key=key, base_url="https://api.openai.com/v1", max_retries=0,
                  organization="", project="", timeout=60,
                  http_client=httpx.Client(trust_env=False, follow_redirects=False, transport=transport))


class APIProvider:
    decision_timeout_seconds = 600

    def __init__(self, ledger, *, model="gpt-6-astra", effort="high", max_output_tokens=16000,
                 max_input_tokens=MAX_INPUT, compact_threshold=175000, client=None, integrity_check=None):
        if model != "gpt-6-astra" or effort != "high":
            raise ValueError("This candidate preserves gpt-6-astra / high; revise the plan for other settings")
        if max_input_tokens != MAX_INPUT:
            raise ValueError("No-count transport must reserve the full documented maximum input size")
        self.model, self.effort, self.ledger = model, effort, ledger
        self.max_output, self.max_input, self.compact_threshold = (
            max_output_tokens, max_input_tokens, compact_threshold)
        self.client = client or api_client()
        self.integrity_check = integrity_check or (lambda: None)
        self.items, self.pending, self.events = [], set(), []
        self.sink = None
        self.input_total = self.output_total = 0
        self.context_tokens = 0
        self.cache_key = "oy1-agi-api9:" + uuid.uuid4().hex
        self.previous_response_id = None
        self.current_image = None

    def set_event_sink(self, sink):
        self.sink = sink

    def emit(self, kind, data):
        if self.sink:
            self.sink(kind, data)
        else:
            self.events.append({"kind": kind, "data": data})

    def drain_events(self):
        events, self.events = self.events, []
        return events

    def preflight(self):
        self.integrity_check()
        timeout = self.remaining_timeout(None, 60)
        try:
            with wall_timeout(timeout):
                model = self.client.models.retrieve(self.model, timeout=timeout)
        except Exception as exc:
            raise RuntimeError(f"API model access preflight failed ({type(exc).__name__})") from None
        if model.id != self.model:
            raise RuntimeError("Requested model is unavailable; no model substitution")
        return {"authentication": "openai_api_key", "model_listing_access": True,
                "inference_access_verified": False, "model": model.id,
                "endpoint": "https://api.openai.com/v1", "subscription_fallback": False}

    def remaining_timeout(self, deadline, maximum):
        self.ledger.check_time()
        remaining = self.ledger.remaining_seconds()
        if deadline is not None:
            decision_left = deadline - self.ledger.clock()
            if decision_left <= 0:
                raise BudgetStop("decision_deadline")
            remaining = min(remaining, decision_left)
        return min(maximum, remaining)

    def request(self, *, compact=False, timeout=600, deadline=None):
        self.integrity_check()
        output_bound = COMPACTION_OUTPUT_TOKENS if compact else self.max_output
        timeout = self.remaining_timeout(deadline, timeout)
        ticket = self.ledger.reserve("compaction" if compact else "response", self.max_input, output_bound)
        try:
            # Reservation writes and integrity checks also consume the shared deadline.
            timeout = self.remaining_timeout(deadline, timeout)
            # Keep original text/tool/opaque items intact. Cache markers are wire metadata.
            request_items = json.loads(json.dumps(self.items))
            boundaries = [i["content"][0] for i in request_items if i.get("role") == "user"
                          and isinstance(i.get("content"), list) and i["content"]
                          and i["content"][0].get("type") == "input_text"]
            for block in boundaries[-4:]:
                block["prompt_cache_breakpoint"] = {"mode": "explicit"}
            if compact:
                request_items.append({"type": "compaction_trigger"})
            elif self.current_image:
                # Older screenshots are represented by their exact grids in retained contexts.
                request_items.append({"role": "user", "content": [self.current_image]})
            self.emit("api_context_identity", {"ledger_request": ticket, "compact": compact,
                      "retained_item_sha256": [hashlib.sha256(json.dumps(i, sort_keys=True).encode()).hexdigest()
                                               for i in self.items],
                      "wire_input_sha256": hashlib.sha256(json.dumps(request_items, sort_keys=True).encode()).hexdigest(),
                      "image_items": int(bool(self.current_image) and not compact),
                      "explicit_breakpoints": min(len(boundaries), 4)})
            common = {"model": self.model,
                      "input": request_items,
                      "instructions": INSTRUCTIONS, "service_tier": "default", "timeout": timeout,
                      "reasoning": {"effort": self.effort, "context": "all_turns"},
                      "prompt_cache_key": self.cache_key,
                      "prompt_cache_options": {"mode": "explicit", "ttl": "30m", **(
                          {"comparison_response_id": self.previous_response_id} if self.previous_response_id else {})},
                      "include": ["reasoning.encrypted_content"],
                      "store": False, "background": False, "truncation": "disabled",
                      "max_output_tokens": output_bound}
            with wall_timeout(timeout):
                if compact:
                    response = self.client.responses.create(**common)
                else:
                    response = self.client.responses.create(
                        **common, tools=schemas(), parallel_tool_calls=False, tool_choice="required",
                    )
            usage = response.usage.model_dump() if response.usage else None
            raw = response.model_dump(exclude_none=True)
            metadata = {"response_id": response.id, "request_id": getattr(response, "_request_id", None),
                        "effective_model": raw.get("model"), "effective_effort":
                        (raw.get("reasoning") or {}).get("effort"),
                        "reasoning_context": (raw.get("reasoning") or {}).get("context"),
                        "prompt_cache_diagnostics": raw.get("prompt_cache_diagnostics"),
                        "service_tier": raw.get("service_tier"), "response_status": raw.get("status")}
            self.ledger.settle(ticket, usage, metadata)
            self.input_total += usage["input_tokens"]
            self.output_total += usage["output_tokens"]
            self.context_tokens = usage["input_tokens"] + usage["output_tokens"]
            self.emit("api_request_completed", {**metadata, "ledger_request": ticket,
                                               "kind": "compaction" if compact else "response", "usage": usage})
            if (raw.get("model") != self.model or metadata["effective_effort"] != self.effort
                    or metadata["reasoning_context"] != "all_turns"):
                raise RuntimeError("Effective model or reasoning not confirmed; no action executed")
            if raw.get("service_tier") != "default":
                raise RuntimeError("Effective Standard service tier not confirmed; no action executed")
            if response.status != "completed":
                raise RuntimeError("Incomplete API response; no action executed")
            self.previous_response_id = response.id
            output = [item.model_dump(exclude_none=True) for item in response.output]
            self.emit("api_response_items", {"ledger_request": ticket, "compact": compact, "output": output})
            if compact and (not output or any(i.get("type") != "compaction" for i in output)):
                raise RuntimeError("Unexpected bounded compaction output; state not replaced")
            self.remaining_timeout(deadline, timeout)
            return output
        except BaseException as exc:
            self.ledger.uncertain(ticket, type(exc).__name__)
            # Raw provider error bodies can contain credentials or task content.
            if isinstance(exc, (BudgetStop, KeyboardInterrupt)):
                raise
            raise RuntimeError(f"API request stopped ({type(exc).__name__}); no automatic retry") from None

    def next(self, context, image_path, timeout, token_allowance):
        if not math.isfinite(timeout) or timeout <= 0:
            raise BudgetStop("decision_deadline")
        deadline = min(self.ledger.work_deadline, self.ledger.clock() + timeout)
        with wall_timeout(self.remaining_timeout(deadline, timeout), "decision_deadline"):
            return self._next(context, image_path, timeout, token_allowance, deadline)

    def _next(self, context, image_path, timeout, token_allowance, deadline):
        if self.pending:
            raise RuntimeError("Unpaired tool results; inference blocked")
        before_i, before_o = self.input_total, self.output_total
        content = [{"type": "input_text", "text": json.dumps(context)}]
        self.current_image = None
        if image_path:
            perception = context.get("perception", {})
            rows = perception.get("rows", [])
            if (not rows or len(rows) != perception.get("height")
                    or any(len(row) != perception.get("width") or any(c not in "0123456789abcdef" for c in row)
                           for row in rows)):
                raise ValueError("A screenshot requires its complete exact pixel grid in retained context")
            self.current_image = {"type": "input_image", "detail": "original", "image_url":
                                  "data:image/png;base64," + base64.b64encode(Path(image_path).read_bytes()).decode()}
        self.items.append({"role": "user", "content": content})
        # Compaction cadence uses the previous observed context, not a separate
        # counting endpoint. Budget safety always uses the full model input limit.
        if self.context_tokens >= self.compact_threshold:
            self.emit("api_compaction_trigger", {"previous_context_tokens": self.context_tokens,
                                                "threshold": self.compact_threshold})
            self.items = self.request(compact=True, timeout=timeout, deadline=deadline)
            if not any(i.get("type") == "compaction" for i in self.items):
                raise RuntimeError("Compaction returned no compaction item")
            self.emit("api_compaction", {"output_item_types": [i.get("type") for i in self.items]})
            # Keep the latest exact observation available after lossy opaque compaction.
            self.items.append({"role": "user", "content": content})
        output = self.request(timeout=timeout, deadline=deadline)
        # Preserve every opaque reasoning/compaction/message item, in provider order.
        self.items.extend(output)
        calls = []
        for item in output:
            if item.get("type") != "function_call":
                if item.get("type") not in ("message", "reasoning", "compaction"):
                    raise RuntimeError("Unexpected provider tool; evaluation rejected")
                continue
            name, identity = item["name"], item["call_id"]
            if not name.startswith("arc_") or identity in self.pending:
                raise RuntimeError("Invalid tool call identity")
            self.pending.add(identity)
            calls.append(ToolCall(name[4:], json.loads(item["arguments"]), identity))
        return ModelReply(calls, self.input_total - before_i, self.output_total - before_o)

    def result(self, call, result):
        if call.call_id not in self.pending:
            raise RuntimeError("Unknown or duplicate tool result")
        self.pending.remove(call.call_id)
        self.emit("api_tool_result", {"call_id": call.call_id, "tool": call.name, "output": result})
        self.items.append({"type": "function_call_output", "call_id": call.call_id,
                           "output": json.dumps(result)})

    def stats(self):
        return {"authentication": "openai_api_key", "provider": "openai-responses",
                "accounted_usage": {"inputTokens": self.input_total, "outputTokens": self.output_total},
                "effective_settings_source": "response_fields", "opaque_state_retained_in_memory": True}

    def finalize(self):
        # Requests are synchronous; expose usage even if a post-response check failed.
        pass

    def close(self):
        self.items.clear()
        self.current_image = None
        self.client.close()
