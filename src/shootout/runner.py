"""Run architectures over questions with a few questions in flight, appending one JSONL record per (architecture, question). Resumable: finished ids are skipped."""
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .graphs import build_architecture, run_question
from .llm import Budget, RunCtx
from .prompts import PROMPTS_VERSION
from .scoring import score_answer

MODEL = "qwen3.5:9b (Q4_K_M) via llama.cpp server"


def record(arch, q, state, ctx, lt):
    answer = (state or {}).get("answer", "")
    return {"id": q["id"], "item_id": q["item_id"], "arch": arch, "type": q["type"], "language": q["language"], "law": q["law"], "gold": q["gold"], "anchor": q["anchor"],
            "answer": answer, "status": (state or {}).get("status") or "crash", "score": score_answer(q, answer, lt), "run": ctx.summary(),
            "calls": ctx.calls, "tools": ctx.tool_calls, "verify": ctx.verify_log, "errors": ctx.errors, "prompts": PROMPTS_VERSION, "model": MODEL}


def done_ids(path):
    p = Path(path)
    return {json.loads(l)["id"] for l in p.read_text().splitlines() if l.strip()} if p.exists() else set()


def run_all(archs, questions, lt, llm, out_dir, concurrency=4, budget=None, log=sys.stderr):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    graphs = {a: build_architecture(a, llm, lt) for a in archs}
    tasks = [(a, q) for q in questions for a in archs if q["id"] not in done_ids(out_dir / f"{a}.jsonl")]
    lock, t0, n = threading.Lock(), time.time(), [0]

    def work(task):
        arch, q = task
        ctx = RunCtx(budget or Budget())
        try:
            state = run_question(graphs[arch], q, ctx)
        except Exception as e:                                                # noqa: BLE001  (an unexpected crash is a result, not the end of the experiment)
            state = {"answer": "", "status": "crash"}
            ctx.errors.append({"node": "harness", "error": f"{type(e).__name__}: {str(e)[:200]}"})
        rec = record(arch, q, state, ctx, lt)
        with lock:
            with open(out_dir / f"{arch}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n[0] += 1
            if n[0] % 8 == 0 or n[0] == len(tasks):
                el = time.time() - t0
                print(f"  {n[0]}/{len(tasks)} runs, {el / 60:.1f} min, eta {el / n[0] * (len(tasks) - n[0]) / 60:.1f} min", file=log, flush=True)

    with ThreadPoolExecutor(concurrency) as ex:
        list(ex.map(work, tasks))
    return len(tasks)


def load_runs(out_dir, archs):
    return {a: [json.loads(l) for l in (Path(out_dir) / f"{a}.jsonl").read_text().splitlines() if l.strip()] for a in archs if (Path(out_dir) / f"{a}.jsonl").exists()}
