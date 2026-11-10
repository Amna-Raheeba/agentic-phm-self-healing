"""Pure-Python graph runner mirroring the LangGraph topology.

Topology: monitor -> diagnosis -> [high/critical: counterfactual -> approval gate] -> report
Retries diagnosis once on transient errors; a max-step guard prevents loops.
This exists so the project runs and is testable with zero heavy dependencies.
See graph_langgraph.py for the equivalent LangGraph wiring.
"""
from __future__ import annotations
import time
from typing import Callable
from .agents.counterfactual import apply_approval, counterfactual_node
from .agents.diagnosis import diagnosis_node
from .agents.monitor import monitor_node
from .agents.report import report_node
from .config import Config
from .observability import RunTrace
from .state import PHMState

Approver = Callable[[PHMState], bool]

class MaxStepsExceeded(RuntimeError): pass

class PHMGraph:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.trace = RunTrace()
    def _run_node(self, name, fn, state):
        if state.get("step_count", 0) >= self.config.max_steps:
            raise MaxStepsExceeded(f"max_steps={self.config.max_steps} exceeded at {name}")
        started = time.perf_counter(); out = fn(state); self.trace.record(name, started, step=out.get("step_count")); return out
    def run(self, state: PHMState, approver: Approver | None = None) -> PHMState:
        state.setdefault("step_count", 0); state.setdefault("errors", [])
        # Defaults for the branch that skips the counterfactual node, so
        # downstream consumers can rely on these keys always being present.
        state.setdefault("counterfactuals", [])
        state.setdefault("approval_required", False)
        state.setdefault("approval_status", "not_required")
        state = self._run_node("monitor", lambda s: monitor_node(s, self.config), state)
        # Diagnosis with one retry — sensor windows occasionally arrive truncated upstream.
        for attempt in range(self.config.max_retries + 1):
            try:
                state = self._run_node("diagnosis", lambda s: diagnosis_node(s, self.config), state); break
            except Exception as exc:
                if attempt >= self.config.max_retries:
                    state["errors"].append(f"diagnosis failed: {exc}"); raise
                state["errors"].append(f"diagnosis retry {attempt+1}: {exc}")
        if state.get("risk_level") in ("high", "critical"):
            state = self._run_node("counterfactual", lambda s: counterfactual_node(s, self.config), state)
            if state.get("approval_required") and state.get("approval_status") == "pending":
                if approver is not None:
                    state = apply_approval(state, bool(approver(state)), approved_by="cli-operator")
                    self.trace.record("human_approval", time.perf_counter(), status=state["approval_status"])
                # No approver supplied: leave pending. Report will state that clearly.
        state = self._run_node("report", report_node, state)
        state["trace"] = self.trace.events
        return state

def run_pipeline(window, run_id: str = "run-001", config: Config | None = None, approver: Approver | None = None) -> PHMState:
    return PHMGraph(config).run({"run_id": run_id, "sensor_window": window}, approver=approver)
