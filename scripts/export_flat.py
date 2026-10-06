#!/usr/bin/env python3
"""Flatten the per-run records into one row per (architecture, question): results/test_runs_flat.jsonl (the table the Hugging Face dataset viewer shows).

  export_flat.py results/runs/test
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from shootout import runner  # noqa: E402
from shootout.graphs import ARCHITECTURES  # noqa: E402

if __name__ == "__main__":
    runs = runner.load_runs(sys.argv[1], ARCHITECTURES)
    qs = {q["id"]: q for q in json.loads((ROOT / "data/questions_test.json").read_text())}
    n = 0
    with open(ROOT / "results/test_runs_flat.jsonl", "w", encoding="utf-8") as f:
        for arch in ARCHITECTURES:
            for r in runs[arch]:
                s, u = r["score"], r["run"]
                row = {"id": r["id"], "architecture": arch, "type": r["type"], "language": r["language"], "law": r["law"], "question": qs[r["id"]]["question"], "gold": r["gold"], "anchor": r["anchor"],
                       "answer": r["answer"], "status": r["status"], "correct": s["correct"], "gold_hit": s["gold_hit"], "cited": s["cited"], "invented": s["invalid"], "extra": s["extra"],
                       "quotes": s["quotes"], "quotes_unsupported": s["quotes_unsupported"], "tokens": u["tokens"], "tokens_in": u["tokens_in"], "tokens_out": u["tokens_out"],
                       "llm_calls": u["llm_calls"], "tool_calls": u["tool_calls"], "tool_failures": u["tool_failures"], "latency_s": round(u["latency_s"], 2), "errors": r["errors"]}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
    print("wrote", n, "rows")
