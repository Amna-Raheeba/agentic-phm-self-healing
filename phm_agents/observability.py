"""Structured logging + run trace. Token/cost tracking is a stub by design:
the core pipeline makes no LLM calls, so cost is 0 unless an LLM adapter is added."""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass, field
logger = logging.getLogger("phm_agents")

def configure_logging(level: int = logging.INFO) -> None:
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(h)
    logger.setLevel(level)

def log_event(event: str, **fields) -> None:
    logger.info(json.dumps({"event": event, **fields}))

@dataclass
class UsageTracker:
    prompt_chars: int = 0
    completion_chars: int = 0
    @property
    def estimated_tokens(self) -> int:
        # Rough 4-chars-per-token heuristic, only for reporting if an LLM is wired in.
        return (self.prompt_chars + self.completion_chars) // 4
    @property
    def estimated_cost_usd(self) -> float:
        return 0.0  # no LLM calls in the default pipeline
    def to_dict(self) -> dict:
        return {"estimated_tokens": self.estimated_tokens, "estimated_cost_usd": self.estimated_cost_usd, "llm_calls": 0}

@dataclass
class RunTrace:
    events: list[dict] = field(default_factory=list)
    usage: UsageTracker = field(default_factory=UsageTracker)
    def record(self, node: str, started: float, **info) -> None:
        self.events.append({"node": node, "duration_ms": round((time.perf_counter()-started)*1000, 2), **info})
        log_event("node_completed", node=node, **info)
