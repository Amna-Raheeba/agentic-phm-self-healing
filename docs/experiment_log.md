# Experiment log

Short notes I keep while building this, so future-me remembers why the
code looks the way it does. Synthetic data throughout.

## 2026-11-05 — First conformal calibration attempt: useless intervals

**Tried:** calibrated the split-conformal interval on assets with total
lives of 110–180 cycles, observing a window at 70–90% of life.
**Happened:** the 90% half-width came out over 100 cycles — wider than
most point estimates, so the interval said almost nothing. The problem
was my calibration population, not conformal itself: this system is
operated on fixed 80-cycle windows (the sample run, the CLI and the
evaluation all use 80), and the estimator's per-cycle loss rate dilutes
badly over longer windows.
**Decision:** calibrate on the population the system actually runs on —
the first 80 cycles of faulty assets with lives of 88–106 cycles — and
document that population in `conformal.py`. Intervals are only claimed
for windows that look like that.

## 2026-11-07 — Failure threshold for imagination: 0.10 kept, with a caveat

**Tried:** health ≤ 0.10 as the imagined failure point, rolling the
last-20-cycle slopes forward.
**Happened:** no action failed at +9 cycles on the demo window, but the
repair scenarios never crossed 0.10 at all — per-sensor loss is capped
at 1.0, so one repaired sensor holds the health index up on its own. My
first reaction was that the simulation was broken; checking the numbers
by hand, it is the model's logic, not a bug.
**Decision:** keep the threshold and report "no failure imagined within
the horizon" for repairs — that *is* the finding — but also record the
imagined health at the horizon for every scenario, otherwise the two
repairs are indistinguishable in the report (cooling repair ends at
0.151, bearing repair at 0.194 on the demo window).

## 2026-11-09 — Coverage experiment, and what the width is telling me

**Tried:** `notebooks/02_conformal_coverage_experiment.py` — calibrate
on 120 assets (seed 2026), measure coverage on 80 held-out assets
(seed 99).
**Happened:** empirical coverage 0.912 / 0.938 / 0.975 at nominal
80 / 90 / 95 — a bit conservative, which the finite-sample correction
explains. Half-widths 69 / 73 / 78 cycles. The point estimator is
optimistically biased by roughly +50 cycles on this population: it
extrapolates the *average* loss rate, while the generator's degradation
accelerates (power 1.35), so assets fail sooner than the average rate
suggests.
**Decision:** ship the intervals with the bias stated openly in the
README and this log, rather than quietly re-tuning the estimator to
make the intervals prettier. Fixing the estimator (a late-window or
slope-aware rate) is now the top roadmap item — conformal stays as the
honest wrapper whatever estimator sits inside it.
