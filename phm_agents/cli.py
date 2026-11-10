"""CLI: python -m phm_agents [--input data/sample_run.csv] [--auto-approve] [--output out.json]"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .config import Config
from .data.generator import generate_run, read_csv
from .graph import run_pipeline
from .observability import configure_logging

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="phm_agents", description="Agentic PHM demo (synthetic data)")
    p.add_argument("--input", help="CSV sensor window; default: generate a synthetic faulty run")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cycles", type=int, default=80)
    p.add_argument("--healthy", action="store_true", help="generate a healthy run instead of faulty")
    p.add_argument("--auto-approve", action="store_true", help="approve repair actions without prompting (demo/CI only)")
    p.add_argument("--approve", action="store_true", help="interactively prompt for approval if required")
    p.add_argument("--output", help="write full JSON result to this path")
    return p

def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    window = read_csv(args.input) if args.input else generate_run(seed=args.seed, cycles=args.cycles, faulty=not args.healthy)
    approver = None
    if args.auto_approve:
        approver = lambda s: True
    elif args.approve:
        def approver(s):  # noqa: F811
            ans = input(f"Approve repair plan for {s.get('run_id')}? [y/N] ")
            return ans.strip().lower() == "y"
    state = run_pipeline(window, run_id="demo-run" if not args.input else Path(args.input).stem,
                         config=Config.from_env(), approver=approver)
    payload = {"report": state["report"], "report_markdown": state["report_markdown"], "trace": state.get("trace", [])}
    print(state["report_markdown"])
    print("\n---\n" + json.dumps(payload["report"], indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {args.output}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
