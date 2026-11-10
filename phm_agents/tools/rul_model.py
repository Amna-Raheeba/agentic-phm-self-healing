"""Heuristic RUL estimator — a baseline, not a trained ML model.

Health index combines (a) deviation of the latest window from the early
baseline, normalised by each sensor's full degradation range, and (b) a small
slope reinforcement. RUL is a linear extrapolation of health loss per cycle.
Intentionally simple and inspectable; swapping in a trained LSTM (as in my
FYP) is on the roadmap in the README.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..state import SensorReading
from .sensor_tools import sensor_stats

WEIGHTS = {"temperature_c": 0.32, "vibration_mm_s": 0.42, "pressure_kpa": 0.26}
# Absolute deviation from baseline that maps to a fully degraded sensor.
# Set above the generator's end-of-life deviation, with headroom, so a run
# near (but not at) failure does not saturate every sensor at exactly 1.0.
DEGRADATION_SCALE = {"temperature_c": 62.0, "vibration_mm_s": 6.4, "pressure_kpa": 88.0}


@dataclass
class RULResult:
    health_index: float
    rul_cycles: float
    risk_score: float
    contributing: list[dict]


class RULEstimator:
    def __init__(self, baseline_cycles: int = 10):
        self.baseline_cycles = baseline_cycles

    def predict(self, window: list[SensorReading]) -> RULResult:
        if len(window) < 6:
            raise ValueError("need at least 6 cycles to estimate RUL")
        stats = sensor_stats(window, self.baseline_cycles)
        contrib, weighted_loss = [], 0.0
        for sensor, weight in WEIGHTS.items():
            deviation = abs(stats[sensor]["latest_mean"] - stats[sensor]["baseline_mean"])
            loss = min(1.0, deviation / DEGRADATION_SCALE[sensor])
            if loss > 0.15:
                loss = min(1.0, loss + min(0.08, abs(stats[sensor]["slope_per_cycle"]) * 0.08))
            weighted_loss += weight * loss
            contrib.append({
                "sensor": sensor, "loss": round(loss, 3), "z": stats[sensor]["z_latest"],
                "slope_per_cycle": stats[sensor]["slope_per_cycle"],
            })
        contrib.sort(key=lambda c: c["loss"], reverse=True)
        health = round(max(0.0, min(1.0, 1.0 - weighted_loss)), 4)
        risk = round(1.0 - health, 4)
        loss_per_cycle = weighted_loss / max(1, len(window) - self.baseline_cycles)
        rul = round(health / loss_per_cycle, 1) if loss_per_cycle > 1e-6 else 999.0
        return RULResult(health_index=health, rul_cycles=min(rul, 999.0), risk_score=risk, contributing=contrib)
