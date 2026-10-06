#!/usr/bin/env python3
"""Fetch the 11 laws from the e-Gov Law API v2 and write data/registry.json.gz (article text included). Needs network; ~1 minute."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from shootout import registry  # noqa: E402

if __name__ == "__main__":
    reg = registry.build_registry()
    out = Path(__file__).resolve().parent.parent / "data" / "registry.json.gz"
    registry.save(reg, out)
    n = sum(len(l["articles"]) for l in reg["laws"])
    print(f"{len(reg['laws'])} laws, {n} main-provision articles, {out.stat().st_size / 1e6:.1f} MB")
    for l in reg["laws"]:
        print(f"  {l['title']:10s} {len(l['articles']):5d} articles  revision {l['revision_id']}")
