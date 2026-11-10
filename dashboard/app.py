"""Streamlit dashboard for the agentic PHM pipeline.

Run it from the repo root:

    pip install streamlit
    streamlit run dashboard/app.py

Streamlit is a dashboard-only dependency — the core pipeline
(``phm_agents``) stays standard-library only. Every number on this page
comes from a live run of ``phm_agents.graph.run_pipeline`` via
``dashboard/helpers.py``; nothing is hardcoded or screenshotted.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Streamlit puts this script's folder (dashboard/) on sys.path, not the repo
# root, so add both explicitly before importing the package or the helpers.
ROOT = Path(__file__).resolve().parent.parent
for _p in (str(ROOT), str(ROOT / "dashboard")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st  # noqa: E402

import helpers  # noqa: E402
from phm_agents.state import SensorReading  # noqa: E402

st.set_page_config(page_title="Agentic PHM — Dashboard", layout="wide")
st.title("Agentic PHM — Self-Healing Predictive Maintenance")
st.caption(
    "Live runs of the monitor → diagnosis → counterfactual → approval → report "
    "pipeline. All data is synthetic (C-MAPSS-style degradation shape), not real engine data."
)

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Scenario")
choice = st.sidebar.radio(
    "Sensor window",
    ["Faulty synthetic run", "Healthy synthetic run", "Upload CSV window"],
)
seed = st.sidebar.number_input("Generator seed", min_value=0, max_value=9999, value=42)
approve = st.sidebar.toggle(
    "Approve repair (demo)",
    value=False,
    help="Supplies a human approver to the pipeline, like the CLI's --auto-approve. "
         "With it off, a high-risk run stays AWAITING HUMAN APPROVAL.",
)

window: list[SensorReading] | None = None
scenario = "faulty"
run_id = "dashboard-faulty"
if choice == "Healthy synthetic run":
    scenario, run_id = "healthy", "dashboard-healthy"
elif choice == "Upload CSV window":
    uploaded = st.sidebar.file_uploader("CSV with cycle + the four sensor columns", type="csv")
    if uploaded is None:
        st.info("Upload a CSV window to run the pipeline on it, or pick a synthetic scenario.")
        st.stop()
    text = uploaded.getvalue().decode("utf-8", errors="replace")
    try:
        window = helpers.window_from_csv_text(text)
    except ValueError as exc:
        st.error(f"Could not read that CSV: {exc}")
        st.stop()
    scenario, run_id = "upload", f"upload-{hashlib.sha256(text.encode()).hexdigest()[:8]}"


@st.cache_data(show_spinner="Running the agent pipeline…")
def _run(scenario_key: str, seed_key: int, approve_key: bool,
         window_key: tuple | None, run_id_key: str):
    win = [dict(r) for r in window_key] if window_key is not None else None
    return helpers.run_scenario(scenario_key, approve=approve_key, seed=seed_key,
                                window=win, run_id=run_id_key)


window_key = tuple(tuple(sorted(r.items())) for r in window) if window is not None else None
state = _run(scenario, int(seed), bool(approve), window_key, run_id)
summary = helpers.metric_summary(state)
report = state["report"]

# ---------------------------------------------------------------- metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Health index", f"{summary['health_index']:.2f}")
c2.metric("RUL estimate", f"{summary['rul_estimate_cycles']:.0f} cycles")
level_pct = f"{summary['interval_level']:.0%}" if summary["interval_level"] else "90%"
c3.metric(f"Conformal {level_pct} interval", summary["interval_text"], help="Split-conformal prediction interval around the RUL point estimate (cycles).")
c4.metric("Risk level", str(summary["risk_level"]).upper(), delta=f"score {summary['risk_score']:.2f}", delta_color="off")

if summary["escalated"]:
    st.warning(
        "ESCALATED — plan on the interval, not the point estimate: the interval's lower "
        "bound is inside the alert window even though the point RUL is above it."
    )

status = summary["approval_status"]
if status == "approved":
    st.success(f"Approval: APPROVED — {summary['disposition']}")
elif status == "pending":
    st.warning(f"Approval: PENDING — {summary['disposition']} "
               "Turn on “Approve repair (demo)” in the sidebar to see the disposition change.")
elif status == "rejected":
    st.error(f"Approval: REJECTED — {summary['disposition']}")
else:
    st.info(f"Approval: not required — {summary['disposition']}")

st.markdown(f"> {report.get('diagnosis_summary', '')}")

# ---------------------------------------------------------------- charts
st.subheader("Sensor window")
picked = st.multiselect("Sensors", helpers.SENSOR_COLUMNS,
                        default=["temperature_c", "vibration_mm_s", "pressure_kpa"])
if picked:
    st.line_chart(helpers.chart_data(state["sensor_window"], picked))
st.caption("One point per cycle. Scales differ per sensor — pressure sits near 1,480 kPa, "
           "so it flattens the others; deselect it to compare temperature and vibration.")

left, right = st.columns(2)
with left:
    st.subheader("Contributing sensors")
    st.caption("Per-sensor health loss from the diagnosis (the explainability surface).")
    chart = helpers.contributors_chart(state)
    if chart:
        st.bar_chart(chart)
        st.dataframe(state["contributing_sensors"], use_container_width=True)
    else:
        st.write("No contributing sensors — the window looks healthy.")
with right:
    st.subheader("Anomalies (monitor)")
    if state.get("anomalies"):
        st.dataframe(state["anomalies"], use_container_width=True)
    else:
        st.write("No anomalies flagged in this window.")

# ---------------------------------------------------------------- repairs
st.subheader("Counterfactual repair options — with failure imagination")
rows = helpers.repair_options_table(state)
if rows:
    st.dataframe(rows, use_container_width=True)
    st.caption("“Imagined failure cycle” rolls the window forward under each scenario: "
               "no action is the baseline every repair has to beat.")
else:
    st.write("No repair options — risk is not high enough to trigger the counterfactual planner.")

# ---------------------------------------------------------------- coverage
coverage = helpers.load_coverage_table(ROOT / "results" / "conformal_coverage.csv")
if coverage:
    with st.expander("Conformal coverage experiment (results/conformal_coverage.csv)"):
        st.dataframe(coverage, use_container_width=True)
        st.caption("Empirical coverage of the split-conformal RUL intervals on held-out "
                   "synthetic assets. Coverage holds; the intervals are wide because the "
                   "heuristic estimator runs optimistic — see docs/experiment_log.md.")

# ---------------------------------------------------------------- detail
with st.expander("Run trace"):
    st.dataframe(helpers.trace_rows(state), use_container_width=True)
with st.expander("Full report (Markdown)"):
    st.markdown(state.get("report_markdown", ""))
with st.expander("Full report (JSON)"):
    st.code(json.dumps(report, indent=2, default=str), language="json")
