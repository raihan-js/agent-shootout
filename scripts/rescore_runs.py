#!/usr/bin/env python3
"""Re-score stored runs from their answer text with the CURRENT scoring (no model is called). Rewrites the JSONL files in place and keeps the replaced score as `score_prev`.
   rescore_runs.py results/runs/dev1"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from shootout import registry  # noqa: E402
from shootout.scoring import score_answer  # noqa: E402
from shootout.tools import LawTools  # noqa: E402

if __name__ == "__main__":
    lt = LawTools(registry.load(ROOT / "data/registry.json.gz"))
    qs = {q["id"]: q for f in ("dev", "test") for q in json.loads((ROOT / f"data/questions_{f}.json").read_text())}
    for f in sorted(Path(sys.argv[1]).glob("*.jsonl")):
        recs, changed = [], 0
        for line in f.read_text().splitlines():
            r = json.loads(line)
            new = score_answer(qs[r["id"]], r["answer"], lt)
            if new != r["score"]:
                changed += 1
                r["score_prev"] = r["score"]
            r["score"] = new
            recs.append(r)
        f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
        print(f"{f.name}: {len(recs)} records, {changed} scores changed")
