#!/usr/bin/env python3
"""Run the TEST split once as LangSmith experiments, one per architecture, and write the same run to results/runs/<out>/<arch>.jsonl.

The experiment IS the run: the target function writes the local record as it goes (so the JSONL is exactly what LangSmith saw) and skips questions already in the JSONL
(resumable after a crash or a quota stop). Nothing is run twice: batched generation at temperature 0 is not exactly repeatable, so two runs would disagree slightly.

  run_test_langsmith.py --create-dataset                     upload the 240 test questions (once)
  run_test_langsmith.py --out results/runs/test [--archs ...] [--no-langsmith]      run (LangSmith key from ~/.config/langsmith/key, never printed)
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
if "--no-langsmith" not in sys.argv:
    if not os.environ.get("LANGSMITH_API_KEY"):
        os.environ["LANGSMITH_API_KEY"] = (Path.home() / ".config/langsmith/key").read_text().strip()
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "agent-shootout")
else:
    os.environ["LANGSMITH_TRACING"] = "false"

from shootout import registry, runner  # noqa: E402
from shootout.graphs import ARCHITECTURES, build_architecture, run_question  # noqa: E402
from shootout.llm import Budget, RunCtx, make_llm  # noqa: E402
from shootout.metrics import rate  # noqa: E402
from shootout.scoring import score_answer  # noqa: E402
from shootout.tools import LawTools  # noqa: E402

DATASET = "shootout-test-240-v1"


def questions():
    return json.loads((ROOT / "data/questions_test.json").read_text())


def create_dataset(client):
    if client.has_dataset(dataset_name=DATASET):
        print(f"dataset {DATASET} exists with {sum(1 for _ in client.list_examples(dataset_name=DATASET))} examples")
        return
    ds = client.create_dataset(DATASET, description="240 questions (120 items x ja/en) over 11 Japanese laws; gold articles from the e-Gov registry. See docs/PREREGISTRATION.md.")
    client.create_examples(dataset_id=ds.id, examples=[
        {"inputs": {"id": q["id"], "question": q["question"], "law": q["law"]}, "outputs": {"gold": q["gold"], "anchor": q["anchor"], "type": q["type"], "language": q["language"]},
         "metadata": {"type": q["type"], "language": q["language"], "item_id": q["item_id"]}} for q in questions()])
    print(f"created {DATASET} with 240 examples")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--create-dataset", action="store_true")
    ap.add_argument("--no-langsmith", action="store_true")
    ap.add_argument("--out", default="results/runs/test")
    ap.add_argument("--archs", nargs="*", default=list(ARCHITECTURES))
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    lt = LawTools(registry.load(ROOT / "data/registry.json.gz"))
    llm = make_llm()
    qmap = {q["id"]: q for q in questions()}
    out_dir = ROOT / a.out
    out_dir.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    if a.no_langsmith:
        n = runner.run_all(a.archs, list(qmap.values()), lt, llm, out_dir, a.concurrency)
        print(f"ran {n} pairs without LangSmith")
        return
    from langsmith import Client, evaluate
    client = Client()
    if a.create_dataset:
        create_dataset(client)
        return
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

    def per_example(arch):
        graph = build_architecture(arch, llm, lt)
        path = out_dir / f"{arch}.jsonl"

        def target(inputs: dict) -> dict:
            q = qmap[inputs["id"]]
            with lock:
                prior = [json.loads(l) for l in path.read_text().splitlines() if l.strip() and json.loads(l)["id"] == q["id"]] if path.exists() else []
            if prior:
                rec = prior[0]
            else:
                ctx = RunCtx(Budget())
                try:
                    state = run_question(graph, q, ctx)
                except Exception as e:                                         # noqa: BLE001
                    state = {"answer": "", "status": "crash"}
                    ctx.errors.append({"node": "harness", "error": f"{type(e).__name__}: {str(e)[:200]}"})
                rec = runner.record(arch, q, state, ctx, lt)
                with lock, open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return {"answer": rec["answer"], "status": rec["status"], "cited": rec["score"]["cited"], "tokens": rec["run"]["tokens"], "llm_calls": rec["run"]["llm_calls"],
                    "tool_calls": rec["run"]["tool_calls"], "latency_s": rec["run"]["latency_s"]}
        return target

    def ev_correct(outputs, reference_outputs, inputs=None):
        s = score_answer({"law": inputs["law"], **reference_outputs}, outputs["answer"], lt)
        return {"key": "correct", "score": int(s["correct"])}

    def ev_invented(outputs, reference_outputs, inputs=None):
        return {"key": "invented", "score": int(bool(score_answer({"law": inputs["law"], **reference_outputs}, outputs["answer"], lt)["invalid"]))}

    def ev_gold_hit(outputs, reference_outputs, inputs=None):
        return {"key": "gold_hit", "score": int(score_answer({"law": inputs["law"], **reference_outputs}, outputs["answer"], lt)["gold_hit"])}

    def ev_tokens(outputs, reference_outputs):
        return {"key": "tokens", "score": outputs["tokens"]}

    def summary(runs, examples):
        flags = [score_answer({"law": e.inputs["law"], **e.outputs}, r.outputs["answer"], lt) for r, e in zip(runs, examples) if r.outputs]
        out = []
        for key, f in (("correct_rate", lambda s: s["correct"]), ("invented_rate", lambda s: bool(s["invalid"])), ("gold_hit_rate", lambda s: s["gold_hit"])):
            r = rate([f(s) for s in flags])
            out.append({"key": key, "score": r["rate"], "comment": f"{r['k']}/{r['n']}, 95% CI [{100 * r['lo']:.1f}%, {100 * r['hi']:.1f}%]"})
        return {"results": out}

    for arch in a.archs:
        res = evaluate(per_example(arch), data=DATASET, evaluators=[ev_correct, ev_invented, ev_gold_hit, ev_tokens], summary_evaluators=[summary],
                       experiment_prefix=f"shootout-{arch}", max_concurrency=a.concurrency, disable_evaluator_tracing=True,
                       metadata={"architecture": arch, "git_commit": commit, "prompts": "v2", "model": runner.MODEL, "preregistration": "docs/PREREGISTRATION.md"})
        print(f"{arch}: experiment {res.experiment_name}", flush=True)


if __name__ == "__main__":
    main()
