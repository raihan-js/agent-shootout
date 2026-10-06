#!/usr/bin/env python3
"""Write data/questions_dev.json (36) and data/questions_test.json (240) from the registry, seed 0. Dev is for prompt work; test is scored once."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from shootout import questions, registry  # noqa: E402

if __name__ == "__main__":
    reg = registry.load(ROOT / "data/registry.json.gz")
    dev, test = questions.build(reg)
    (ROOT / "data/questions_dev.json").write_text(json.dumps(dev, ensure_ascii=False, indent=1) + "\n")
    (ROOT / "data/questions_test.json").write_text(json.dumps(test, ensure_ascii=False, indent=1) + "\n")
    for name, qs in (("dev", dev), ("test", test)):
        print(name, len(qs), dict(Counter(q["type"] for q in qs)), dict(Counter(q["language"] for q in qs)), "laws:", dict(Counter(q["law"] for q in qs if q["language"] == "ja")))
