"""Failure imagination: roll the current window forward, with and without repair.

This is the "failure imagination" idea from my FYP, turned into an agent
step. Instead of only asking the estimator "how long is left?", we simulate
the next N cycles of sensor trajectories and watch the health index evolve:

- **no action** — every sensor keeps its recent (last-20-cycle) slope.
- **one scenario per counterfactual repair** — the repair's target sensor
  is reset most of the way back toward its early baseline and afterwards
  degrades at 15% of its recent slope (a repaired part is not new, but it
  is close); other sensors keep their slopes. The load-reduction option
  has no single target sensor, so it instead slows every slope to 60%.

The imagined failure cycle is the first future cycle where the imagined
health index falls to the failure threshold, or None if the asset survives
the horizon. Trajectories are scored with the same per-sensor loss weights
as the RUL estimator, so the imagined futures are consistent with the
diagnosis they follow from. Slopes are extrapolated linearly — degradation
in the generator accelerates, so treat the no-action failure cycle as
optimistic, not exact.
"""
from __future__ import annotations

from ..state import Counterfactual, PHMState, SensorReading
from ..tools.rul_model import DEGRADATION_SCALE, WEIGHTS
from ..tools.sensor_tools import sensor_stats

RECENT_WINDOW = 20
REPAIR_RESIDUAL = 0.20   # repair leaves 20% of the target sensor's deviation
REPAIR_SLOPE_FACTOR = 0.15
LOAD_SLOPE_FACTOR = 0.60


def _recent_slope(values: list[float], window: int = RECENT_WINDOW) -> float:
    xs = values[-window:]
    n = len(xs)
    if n < 2:
        return 0.0
    xm, ym = (n - 1) / 2, sum(xs) / n
    denom = sum((i - xm) ** 2 for i in range(n)) or 1.0
    return sum((i - xm) * (y - ym) for i, y in enumerate(xs)) / denom


def _health(values: dict[str, float], baseline: dict[str, float]) -> float:
    loss = sum(weight * min(1.0, abs(values[sensor] - baseline[sensor]) / DEGRADATION_SCALE[sensor])
               for sensor, weight in WEIGHTS.items())
    return max(0.0, min(1.0, 1.0 - loss))


def _roll_forward(latest: dict[str, float], baseline: dict[str, float],
                  slopes: dict[str, float], horizon: int, failure_health: float,
                  target_sensor: str | None = None, slope_factor: float = 1.0) -> tuple[int | None, float]:
    """Returns (first cycle at/below failure_health or None, health at horizon).

    Note: per-sensor loss is capped at 1.0 (as in the RUL estimator), so a
    repaired sensor can hold the health index above the failure threshold
    for the whole horizon — that is reported as surviving the horizon,
    with health_at_horizon still distinguishing between repairs.
    """
    failure = None
    health = _health(latest, baseline)
    for t in range(1, horizon + 1):
        imagined = {}
        for sensor in WEIGHTS:
            start = latest[sensor]
            if sensor == target_sensor:
                start = baseline[sensor] + (latest[sensor] - baseline[sensor]) * REPAIR_RESIDUAL
            imagined[sensor] = start + slopes[sensor] * slope_factor * t
        health = _health(imagined, baseline)
        if failure is None and health <= failure_health:
            failure = t
    return failure, round(health, 3)


def imagine_failures(window: list[SensorReading], counterfactuals: list[Counterfactual],
                     horizon: int = 120, failure_health: float = 0.10,
                     baseline_cycles: int = 10) -> list[dict]:
    """Imagined failure cycle per scenario: no-action first, then one per repair."""
    stats = sensor_stats(window, baseline_cycles)
    latest = {s: stats[s]["latest_mean"] for s in WEIGHTS}
    baseline = {s: stats[s]["baseline_mean"] for s in WEIGHTS}
    slopes = {s: _recent_slope([float(r[s]) for r in window]) for s in WEIGHTS}

    scenarios = []
    no_action, no_action_health = _roll_forward(latest, baseline, slopes, horizon, failure_health)
    scenarios.append({"scenario": "no_action", "action": "No action — continue as-is",
                      "imagined_failure_cycle": no_action, "cycles_bought": 0,
                      "health_at_horizon": no_action_health, "horizon_cycles": horizon})
    for plan in counterfactuals:
        target = plan.get("target_sensor")
        if target in WEIGHTS:
            # Reset the target sensor's level toward baseline (in
            # _roll_forward) and let it degrade slower from there.
            repaired_slopes = dict(slopes)
            repaired_slopes[target] = slopes[target] * REPAIR_SLOPE_FACTOR
            failure, health_end = _roll_forward(latest, baseline, repaired_slopes, horizon,
                                                failure_health, target_sensor=target, slope_factor=1.0)
        else:
            # Load reduction (or anything without a single target): slower everything.
            failure, health_end = _roll_forward(latest, baseline, slopes, horizon, failure_health,
                                                slope_factor=LOAD_SLOPE_FACTOR)
        bought = (failure - no_action) if (failure is not None and no_action is not None) else None
        scenarios.append({"scenario": f"repair:{target}", "action": plan.get("action", ""),
                          "imagined_failure_cycle": failure, "cycles_bought": bought,
                          "health_at_horizon": health_end, "horizon_cycles": horizon})
    return scenarios


def failure_imagination_node(state: PHMState, horizon: int = 120,
                             failure_health: float = 0.10, baseline_cycles: int = 10) -> PHMState:
    """Standalone node wrapper around imagine_failures (used by the tests);
    in the graph itself the counterfactual node calls imagine_failures
    directly, so imagination and planning share one step."""
    state["failure_imagination"] = imagine_failures(
        state["sensor_window"], state.get("counterfactuals", []),
        horizon=horizon, failure_health=failure_health, baseline_cycles=baseline_cycles)
    return state
