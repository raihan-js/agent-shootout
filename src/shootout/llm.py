"""The model client and per-run accounting.

One `RunCtx` per question, shared by every model call in that run: it records tokens and wall time per call, tool calls, and enforces the budget (a cap on tokens and on
calls). `call` returns None when the budget is spent or the server fails, and the graph then ends the run with that status; a run never raises because of the model.
"""
import re
import threading
import time
from dataclasses import dataclass, field

DEFAULT_URL = "http://127.0.0.1:11600/v1"
_THINK = re.compile(r"<think>.*?</think>", re.S)


def make_llm(base_url=DEFAULT_URL, temperature=0.0, max_tokens=400, timeout=240, seed=0):
    """The local qwen3.5:9b behind llama-server (OpenAI-compatible); see scripts/serve_llm.sh. Thinking is switched off in the server's chat-template arguments."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(base_url=base_url, api_key="local", model="qwen3.5-9b", temperature=temperature, max_tokens=max_tokens, timeout=timeout, max_retries=0, seed=seed)


def clean(text):
    return _THINK.sub("", text or "").strip()


@dataclass
class Budget:
    max_tokens: int = 24000          # prompt + completion tokens over the whole run
    max_calls: int = 20              # model calls over the whole run


@dataclass
class RunCtx:
    budget: Budget = field(default_factory=Budget)
    calls: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    verify_log: list = field(default_factory=list)
    t0: float = field(default_factory=time.perf_counter)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def tokens(self):
        return sum(c["in"] + c["out"] for c in self.calls)

    def exhausted(self):
        return self.tokens >= self.budget.max_tokens or len(self.calls) >= self.budget.max_calls

    def call(self, node, runnable, messages):
        if self.exhausted():
            return None
        t = time.perf_counter()
        try:
            msg = runnable.invoke(messages)
        except Exception as e:                                           # noqa: BLE001  (a server error ends the run, it does not crash the harness)
            with self._lock:
                self.errors.append({"node": node, "error": f"{type(e).__name__}: {str(e)[:160]}"})
            return None
        u = getattr(msg, "usage_metadata", None) or {}
        with self._lock:
            self.calls.append({"node": node, "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "ms": 1000 * (time.perf_counter() - t)})
        return msg

    def summary(self):
        return {"llm_calls": len(self.calls), "tool_calls": len(self.tool_calls), "tokens_in": sum(c["in"] for c in self.calls), "tokens_out": sum(c["out"] for c in self.calls),
                "tokens": self.tokens, "latency_s": time.perf_counter() - self.t0, "errors": len(self.errors),
                "tool_failures": sum(not t["ok"] for t in self.tool_calls)}
