"""Monitor agent: validates the window and surfaces anomalous sensors."""
from __future__ import annotations
from ..config import Config
from ..state import PHMState
from ..tools.sensor_tools import detect_anomalies, sensor_stats

def monitor_node(state: PHMState, config: Config | None = None) -> PHMState:
    cfg = config or Config()
    window = state.get("sensor_window") or []
    if len(window) < 6:
        raise ValueError("sensor_window must contain at least 6 cycles")
    state["sensor_stats"] = sensor_stats(window, cfg.baseline_cycles)
    state["anomalies"] = detect_anomalies(window, cfg.baseline_cycles, cfg.anomaly_z_threshold)
    state["step_count"] = state.get("step_count", 0) + 1
    return state
