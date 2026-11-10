"""Notebook 01 — What does one synthetic window actually look like?

Question: before trusting any agent output, I want to see a single faulty
window end to end — which sensors move, when the anomalies fire, and what
the heuristic estimator blames. This is the sanity check I rerun whenever
the generator or the estimator changes.

Date: 2026-11-04
Run:    python notebooks/01_explore_synthetic_window.py
Writes: results/window_summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from phm_agents.data.generator import read_csv
from phm_agents.tools.rul_model import RULEstimator
from phm_agents.tools.sensor_tools import detect_anomalies, sensor_stats

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main() -> int:
    window = read_csv(Path(__file__).resolve().parents[1] / "phm_agents" / "data" / "sample_run.csv")
    print(f"window: {len(window)} cycles, cycle {window[0]['cycle']}..{window[-1]['cycle']}")

    stats = sensor_stats(window)
    print("\nsensor            baseline -> latest      slope/cycle    z")
    for sensor, s in stats.items():
        print(f"{sensor:<16} {s['baseline_mean']:>9.2f} -> {s['latest_mean']:<9.2f} "
              f"{s['slope_per_cycle']:>10.4f} {s['z_latest']:>8.1f}")

    anomalies = detect_anomalies(window)
    print(f"\nanomalies (|z| >= 2.5): {[a['sensor'] for a in anomalies]}")

    result = RULEstimator().predict(window)
    print(f"\nhealth index {result.health_index:.3f} | RUL {result.rul_cycles:.1f} cycles "
          f"| risk {result.risk_score:.3f}")
    print("contributors (per-sensor loss, highest first):")
    for c in result.contributing:
        print(f"  {c['sensor']:<16} loss {c['loss']:.3f}")

    RESULTS.mkdir(exist_ok=True)
    summary = {"window_cycles": len(window), "stats": stats, "anomalies": anomalies,
               "health_index": result.health_index, "rul_cycles": result.rul_cycles,
               "risk_score": result.risk_score, "contributing": result.contributing}
    out = RESULTS / "window_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(RESULTS.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
