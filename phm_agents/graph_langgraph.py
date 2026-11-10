"""Optional LangGraph adapter. Import only if langgraph is installed.

    pip install langgraph
The node functions are shared with graph.py, so behaviour does not diverge.
"""
from __future__ import annotations
from .config import Config
from .state import PHMState

def build_langgraph(config: Config | None = None):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise ImportError("langgraph is not installed; use phm_agents.graph.PHMGraph (pure python) or pip install langgraph") from exc
    from .agents.counterfactual import counterfactual_node
    from .agents.diagnosis import diagnosis_node
    from .agents.monitor import monitor_node
    from .agents.report import report_node
    cfg = config or Config()
    g = StateGraph(PHMState)
    g.add_node("monitor", lambda s: monitor_node(s, cfg))
    g.add_node("diagnosis", lambda s: diagnosis_node(s, cfg))
    g.add_node("counterfactual", lambda s: counterfactual_node(s, cfg))
    g.add_node("report", report_node)
    g.add_edge(START, "monitor"); g.add_edge("monitor", "diagnosis")
    g.add_conditional_edges("diagnosis", lambda s: "counterfactual" if s.get("risk_level") in ("high", "critical") else "report",
                            {"counterfactual": "counterfactual", "report": "report"})
    g.add_edge("counterfactual", "report"); g.add_edge("report", END)
    return g.compile()
