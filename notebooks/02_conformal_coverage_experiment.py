"""Notebook 02 — Do the conformal RUL intervals actually cover?

Question: the split-conformal interval is only worth reporting if its
empirical coverage on held-out generated assets lands near the nominal
level. This experiment calibrates on one seed split (n=120) and measures
coverage on a separate test split (n=80) at 80/90/95%, then plots the
90% intervals for 20 test assets against their true RUL.

What I expect to see (and did — see docs/experiment_log.md): coverage
close to nominal, but wide intervals. The heuristic extrapolates the
average degradation rate while the generator's degradation accelerates,
so the point estimates run optimistic and conformal honestly prices
that in as width.

Date: 2026-11-09
Run:    python notebooks/02_conformal_coverage_experiment.py
Writes: results/conformal_coverage.csv, results/rul_interval_plot.png
        (plot is skipped, not failed, if matplotlib is not installed)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from phm_agents.tools.conformal import _half_width, calibration_pairs, empirical_coverage

RESULTS = Path(__file__).resolve().parents[1] / "results"
LEVELS = (0.80, 0.90, 0.95)
CAL_SEED, TEST_SEED = 2026, 99


def write_coverage_csv() -> list[dict]:
    rows = []
    for level in LEVELS:
        r = empirical_coverage(level, n_calibration=120, cal_seed=CAL_SEED,
                               n_test=80, test_seed=TEST_SEED)
        rows.append(r)
        print(f"level {level:.0%}: half-width {r['half_width']:>5.1f} cycles, "
              f"empirical coverage {r['empirical_coverage']:.3f} (n_test={r['n_test']})")
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "conformal_coverage.csv").open("w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=["level", "half_width", "n_calibration", "n_test", "empirical_coverage"])
        wtr.writeheader()
        wtr.writerows(rows)
    print(f"wrote results/conformal_coverage.csv")
    return rows


def write_plot() -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed — skipping results/rul_interval_plot.png")
        return
    half = _half_width(0.90, 120, CAL_SEED, 10)
    pairs = sorted(calibration_pairs(20, TEST_SEED)[:20])
    preds = [p for p, _ in pairs]
    trues = [t for _, t in pairs]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.errorbar(range(len(pairs)), preds, yerr=half, fmt="o", ms=4, capsize=3,
                label="predicted RUL with 90% conformal interval")
    ax.plot(range(len(pairs)), trues, "x", ms=7, label="true RUL")
    ax.set_xlabel("held-out test asset (sorted by predicted RUL)")
    ax.set_ylabel("cycles")
    ax.set_title("RUL point estimate vs 90% split-conformal interval (synthetic data)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / "rul_interval_plot.png", dpi=150)
    print("wrote results/rul_interval_plot.png")


def main() -> int:
    write_coverage_csv()
    write_plot()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
