#!/usr/bin/env python3
"""Write a Mermaid diagram of each architecture to docs/graphs/<name>.mmd, generated from the compiled graphs (never drawn by hand). No model server is needed."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from shootout import registry  # noqa: E402
from shootout.graphs import ARCHITECTURES, build_architecture  # noqa: E402
from shootout.llm import make_llm  # noqa: E402
from shootout.tools import LawTools  # noqa: E402

if __name__ == "__main__":
    out = ROOT / "docs" / "graphs"
    out.mkdir(parents=True, exist_ok=True)
    lt = LawTools(registry.load(ROOT / "data/registry.json.gz"))
    for name in ARCHITECTURES:
        g = build_architecture(name, make_llm(), lt)
        (out / f"{name}.mmd").write_text(g.get_graph().draw_mermaid(), encoding="utf-8")
        print("wrote", out / f"{name}.mmd")
