#!/usr/bin/env python3
"""Run architectures over a question set against the local model server (scripts/serve_llm.sh must be running).

  run_arch.py --split dev --out results/runs/dev1 [--archs react ...] [--limit 4] [--concurrency 4]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from shootout import registry, runner  # noqa: E402
from shootout.graphs import ARCHITECTURES  # noqa: E402
from shootout.llm import Budget, make_llm  # noqa: E402
from shootout.tools import LawTools  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--archs", nargs="*", default=list(ARCHITECTURES))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=24000)
    a = ap.parse_args()
    qs = json.loads((ROOT / f"data/questions_{a.split}.json").read_text())
    if a.limit:
        qs = qs[:a.limit]
    lt = LawTools(registry.load(ROOT / "data/registry.json.gz"))
    n = runner.run_all(a.archs, qs, lt, make_llm(), ROOT / a.out, a.concurrency, Budget(max_tokens=a.max_tokens))
    print(f"ran {n} (architecture, question) pairs into {a.out}")
