"""Seeded synthetic sensor generator mimicking C-MAPSS-style degradation.

Not NASA data. A healthy run stays near baseline with noise. A faulty run is
flat until `degradation_start`, then temperature/vibration rise and pressure
drifts as the fault progresses — the shape (not the values) is what matters
for testing the agents downstream.
"""
from __future__ import annotations
import csv, math, random
from pathlib import Path
from ..state import SensorReading

BASELINE = {"temperature_c": 612.0, "vibration_mm_s": 3.1, "pressure_kpa": 1480.0, "load_pct": 74.0}

def generate_run(seed: int = 42, cycles: int = 80, faulty: bool = True,
                 degradation_start: int = 35, severity: float = 1.0) -> list[SensorReading]:
    rng = random.Random(seed)
    rows: list[SensorReading] = []
    for cycle in range(1, cycles + 1):
        progress = 0.0
        if faulty and cycle > degradation_start:
            # Exponential-ish progression, capped so late cycles do not explode.
            progress = min(1.0, ((cycle - degradation_start) / max(1, cycles - degradation_start)) ** 1.35) * severity
        rows.append({
            "cycle": cycle,
            "temperature_c": round(BASELINE["temperature_c"] + progress * 49 + rng.gauss(0, 2.4), 3),
            "vibration_mm_s": round(max(0.4, BASELINE["vibration_mm_s"] + progress * 5.1 + rng.gauss(0, 0.22)), 3),
            "pressure_kpa": round(BASELINE["pressure_kpa"] - progress * 68 + rng.gauss(0, 7.0), 3),
            "load_pct": round(BASELINE["load_pct"] + math.sin(cycle / 9.0) * 3 + rng.gauss(0, 1.1), 3),
        })
    return rows

def generate_labelled_runs(n_per_class: int = 12, seed: int = 7, cycles: int = 80) -> list[tuple[bool, list[SensorReading]]]:
    """Return (is_faulty, window) pairs for evaluation. Faulty runs vary in onset/severity."""
    out = []
    for i in range(n_per_class):
        out.append((False, generate_run(seed=seed + 1000 + i, cycles=cycles, faulty=False)))
        out.append((True, generate_run(seed=seed + i, cycles=cycles, faulty=True,
                                        degradation_start=25 + (i % 4) * 5, severity=0.9 + (i % 3) * 0.25)))
    return out

def write_csv(rows: list[SensorReading], path: str | Path) -> Path:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wtr.writeheader(); wtr.writerows(rows)
    return p

def read_csv(path: str | Path) -> list[SensorReading]:
    with Path(path).open(newline="") as f:
        return [{"cycle": int(r["cycle"]), "temperature_c": float(r["temperature_c"]),
                 "vibration_mm_s": float(r["vibration_mm_s"]), "pressure_kpa": float(r["pressure_kpa"]),
                 "load_pct": float(r["load_pct"])} for r in csv.DictReader(f)]

if __name__ == "__main__":
    write_csv(generate_run(), Path(__file__).with_name("sample_run.csv"))
    print("wrote sample_run.csv")
