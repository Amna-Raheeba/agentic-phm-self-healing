"""Detection evaluation on synthetic labelled runs.

A run counts as 'detected' if the pipeline labels it high/critical risk.
Ground truth is the generator's faulty flag — so this measures whether the
pipeline catches the degradation shape it was designed for, nothing more.
It is NOT a benchmark on real engines.
"""
from __future__ import annotations
import json
from ..data.generator import generate_labelled_runs
from ..graph import run_pipeline

def evaluate(n_per_class: int = 12, seed: int = 7) -> dict:
    tp = fp = tn = fn = 0
    for is_faulty, window in generate_labelled_runs(n_per_class=n_per_class, seed=seed):
        state = run_pipeline(window, run_id="eval", approver=lambda s: True)
        detected = state.get("risk_level") in ("high", "critical")
        if is_faulty and detected: tp += 1
        elif is_faulty: fn += 1
        elif detected: fp += 1
        else: tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"dataset": "synthetic (generator, labelled)", "n_runs": tp+fp+tn+fn,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(precision, 3), "recall": round(recall, 3),
            "note": "Synthetic-only. Do not cite as real-world / NASA C-MAPSS performance."}

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
