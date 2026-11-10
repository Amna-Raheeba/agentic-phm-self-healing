"""Deterministic sensor statistics and anomaly detection (z-score vs early baseline)."""
from __future__ import annotations
import math
from ..state import SensorReading
SENSORS = ("temperature_c", "vibration_mm_s", "pressure_kpa", "load_pct")

def _mean(xs): return sum(xs) / max(1, len(xs))
def _std(xs, mu):
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / max(1, len(xs))) or 1e-9
def _slope(xs):
    n = len(xs)
    if n < 2: return 0.0
    xm, ym = (n - 1) / 2, _mean(xs)
    denom = sum((i - xm) ** 2 for i in range(n)) or 1.0
    return sum((i - xm) * (y - ym) for i, y in enumerate(xs)) / denom

def sensor_stats(window: list[SensorReading], baseline_cycles: int = 10) -> dict[str, dict[str, float]]:
    stats = {}
    for s in SENSORS:
        vals = [float(r[s]) for r in window]
        base = vals[:baseline_cycles]
        mu, sd = _mean(base), _std(base, _mean(base))
        latest = _mean(vals[-5:]) if len(vals) >= 5 else _mean(vals)
        stats[s] = {"baseline_mean": round(mu, 4), "baseline_std": round(sd, 4),
                    "latest_mean": round(latest, 4), "slope_per_cycle": round(_slope(vals), 5),
                    "z_latest": round((latest - mu) / sd, 3), "max": round(max(vals), 3), "min": round(min(vals), 3)}
    return stats

def detect_anomalies(window: list[SensorReading], baseline_cycles: int = 10, z_threshold: float = 2.5) -> list[dict]:
    stats = sensor_stats(window, baseline_cycles)
    # load_pct is operational, not a degradation signal — exclude it from anomalies.
    return [{"sensor": s, "z": v["z_latest"], "latest_mean": v["latest_mean"], "baseline_mean": v["baseline_mean"]}
            for s, v in stats.items() if s != "load_pct" and abs(v["z_latest"]) >= z_threshold]
