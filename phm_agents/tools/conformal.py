"""Split-conformal prediction intervals for the RUL estimate.

Why this exists: the heuristic RUL estimator returns a single number, and a
single number invites false confidence. Split conformal wraps it in an
interval with a marginal coverage guarantee that does not depend on the
estimator being good — only on calibration and future runs being drawn from
the same distribution. If the estimator is biased, the interval gets wide
and says so. That is the point.

Calibration population (read this before trusting the interval):
the system is operated on 80-cycle windows (sample_run.csv, the CLI default
and the evaluation all use 80), so calibration windows are the first 80
cycles of synthetic faulty assets whose total lives run 88–106 cycles,
with degradation starting at cycle 30–40. The true RUL of a calibration
window is therefore `life - 80`. Intervals are only meaningful for windows
that look like they came from that population — late-stage, faulty assets.
Coverage on a held-out split is measured in
notebooks/02_conformal_coverage_experiment.py and results/.

Method: absolute-residual split conformal. The half-width is the
ceil((n + 1) * level)-th smallest absolute residual on the calibration
split, and the interval is point ± half-width, clipped at 0 (RUL cannot
be negative). Calibration is cached per (level, n, seed) — it is the
same computation every run otherwise.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache

from ..data.generator import generate_run
from ..state import SensorReading
from .rul_model import RULEstimator

WINDOW_CYCLES = 80
LIFE_RANGE = (88, 106)
START_RANGE = (30, 40)


@dataclass
class ConformalInterval:
    level: float
    lower: float
    upper: float
    half_width: float
    n_calibration: int


def calibration_pairs(n: int, seed: int, baseline_cycles: int = 10) -> list[tuple[float, float]]:
    """(predicted RUL, true RUL) pairs on held-out generated assets."""
    rng = random.Random(seed)
    estimator = RULEstimator(baseline_cycles)
    pairs = []
    for i in range(n):
        life = rng.randint(*LIFE_RANGE)
        start = rng.randint(*START_RANGE)
        full = generate_run(seed=seed + 1000 + i * 13, cycles=life, faulty=True,
                            degradation_start=start, severity=1.0)
        window: list[SensorReading] = full[:WINDOW_CYCLES]
        pairs.append((estimator.predict(window).rul_cycles, float(life - WINDOW_CYCLES)))
    return pairs


def _residual_quantile(residuals: list[float], level: float) -> float:
    ordered = sorted(residuals)
    rank = min(len(ordered), math.ceil((len(ordered) + 1) * level))
    return ordered[rank - 1]


@lru_cache(maxsize=8)
def _half_width(level: float, n_calibration: int, seed: int, baseline_cycles: int) -> float:
    pairs = calibration_pairs(n_calibration, seed, baseline_cycles)
    return _residual_quantile([abs(pred - true) for pred, true in pairs], level)


def rul_interval(point_rul: float, level: float = 0.90, n_calibration: int = 120,
                 seed: int = 2026, baseline_cycles: int = 10) -> ConformalInterval:
    """Interval for one point estimate, calibrated on generated held-out runs."""
    half = _half_width(level, n_calibration, seed, baseline_cycles)
    return ConformalInterval(level=level, lower=round(max(0.0, point_rul - half), 1),
                             upper=round(point_rul + half, 1), half_width=round(half, 1),
                             n_calibration=n_calibration)


def empirical_coverage(level: float, n_calibration: int = 120, cal_seed: int = 2026,
                       n_test: int = 80, test_seed: int = 99, baseline_cycles: int = 10) -> dict:
    """Coverage of the calibrated interval on a separate generated split."""
    half = _half_width(level, n_calibration, cal_seed, baseline_cycles)
    test_pairs = calibration_pairs(n_test, test_seed, baseline_cycles)
    covered = sum(1 for pred, true in test_pairs if abs(pred - true) <= half)
    return {"level": level, "half_width": round(half, 1), "n_calibration": n_calibration,
            "n_test": n_test, "empirical_coverage": round(covered / len(test_pairs), 3)}
