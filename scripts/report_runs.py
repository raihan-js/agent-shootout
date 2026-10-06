#!/usr/bin/env python3
"""Print a comparison table for a runs directory.   report_runs.py results/runs/dev1 [--by type|language]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from shootout import metrics, runner  # noqa: E402
from shootout.graphs import ARCHITECTURES  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--by", choices=["type", "language"])
    a = ap.parse_args()
    runs = runner.load_runs(a.dir, ARCHITECTURES)
    groups = {"all": runs} if not a.by else {k: {arch: [r for r in rs if r[a.by] == k] for arch, rs in runs.items()} for k in sorted({r[a.by] for rs in runs.values() for r in rs})}
    for gname, g in groups.items():
        print(f"\n== {gname}")
        print(f"{'architecture':13s} {'n':>4s} | {'correct':>26s} | {'precise':>8s} | {'invented answers':>16s} | {'no tool':>7s} | {'not answered':>12s} | {'tokens':>7s} {'calls':>5s} {'p50 s':>6s} | tok/correct")
        for arch, rs in g.items():
            if not rs:
                continue
            s = metrics.summarise(rs)
            print(f"{arch:13s} {s['n']:4d} | {metrics.fmt(s['correct']):>26s} | {100 * s['precise']['rate']:7.1f}% | {s['invented']['k']:4d} ({100 * s['invented']['rate']:4.1f}%)    | {100 * s['no_tool_runs']['rate']:6.1f}% | "
                  f"{s['not_answered']['k']:5d} ({100 * s['not_answered']['rate']:4.1f}%) | {s['tokens']['mean']:7.0f} {s['llm_calls']['mean']:5.1f} {s['latency_p50']:6.1f} | {s['tokens_per_correct'] or float('nan'):.0f}")
