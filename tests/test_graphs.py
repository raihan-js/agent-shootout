import pytest
from fakes import FakeChat, say, tool_call

from shootout import graphs
from shootout.llm import Budget, RunCtx
from shootout.scoring import score_answer
from shootout.tools import LawTools

Q = {"question": "民法で契約の解除を定めている条文はどれですか。", "law": "民法", "gold": ["5"], "anchor": []}


def run(arch, script, small_registry, budget=None, q=Q):
    llm = FakeChat(script)
    lt = LawTools(small_registry)
    ctx = RunCtx(budget or Budget())
    out = graphs.run_question(graphs.build_architecture(arch, llm, lt), q, ctx)
    return out, ctx, llm, lt


# ---- A: ReAct -----------------------------------------------------------------------------------------
def test_react_searches_opens_and_answers(small_registry):
    out, ctx, llm, lt = run("react", [tool_call("search_articles", query="契約の解除", law="民法"), tool_call("get_article", law="民法", article="5"), say("民法第五条です。")], small_registry)
    assert out["status"] == "answered" and "第五条" in out["answer"]
    assert [c["node"] for c in ctx.calls] == ["react.agent"] * 3 and [t["name"] for t in ctx.tool_calls] == ["search_articles", "get_article"]
    assert all(t["ok"] for t in ctx.tool_calls) and ctx.summary()["tool_failures"] == 0
    assert score_answer(Q, out["answer"], lt)["correct"]


def test_react_iteration_cap_forces_an_answer(small_registry, monkeypatch):
    monkeypatch.setitem(graphs.MAX_ITERS, "react", 2)
    out, ctx, llm, _ = run("react", [tool_call("search_articles", query="a"), tool_call("search_articles", query="b"), say("民法第五条です。")], small_registry)
    assert out["status"] == "answered" and [c["node"] for c in ctx.calls] == ["react.agent", "react.agent", "react.force"]
    assert "step limit" in llm.seen[-1][-1].content


def test_budget_exhaustion_ends_the_run_with_a_status_not_an_error(small_registry):
    out, ctx, _, _ = run("react", [tool_call("search_articles", query="a")], small_registry, budget=Budget(max_tokens=50))
    assert out["status"] == "budget_exhausted" and out["answer"] == "" and len(ctx.calls) == 1


def test_failed_tool_calls_are_counted(small_registry):
    out, ctx, _, _ = run("react", [tool_call("get_article", law="民法", article="99"), tool_call("verify_citation", law="民法", article="98"), say("見つかりません。")], small_registry)
    assert [t["ok"] for t in ctx.tool_calls] == [False, False] and ctx.summary()["tool_failures"] == 2 and out["status"] == "answered"


def test_bad_tool_arguments_do_not_crash(small_registry):
    out, ctx, _, _ = run("react", [tool_call("get_article", wrong="x"), say("民法第五条")], small_registry)
    assert ctx.tool_calls[0]["ok"] is False and out["status"] == "answered"


def test_server_errors_end_the_run_as_llm_error(small_registry):
    class Boom(FakeChat):
        def invoke(self, messages):
            raise ConnectionError("server down")
    ctx = RunCtx()
    out = graphs.run_question(graphs.build_architecture("react", Boom([]), LawTools(small_registry)), Q, ctx)
    assert out["status"] == "llm_error" and ctx.errors and ctx.errors[0]["error"].startswith("ConnectionError")


# ---- B: plan and execute ------------------------------------------------------------------------------
def test_plan_execute_runs_each_step_then_synthesises(small_registry):
    script = [say('{"steps": ["find the article on 契約の解除", "check it"]}'), tool_call("get_article", law="民法", article="5"), say("found: id 5"), say("checked: 5"), say("民法第五条です。")]
    out, ctx, llm, _ = run("plan_execute", script, small_registry)
    assert out["status"] == "answered" and [c["node"] for c in ctx.calls] == ["planner", "step.agent", "step.agent", "step.agent", "synth"]
    assert "found: id 5" in llm.seen[-1][0].content and "checked: 5" in llm.seen[-1][0].content           # the synthesizer sees every step's result


def test_plan_execute_falls_back_when_the_plan_is_not_json(small_registry):
    out, ctx, _, _ = run("plan_execute", [say("I will just look it up."), say("found: id 5"), say("民法第五条です。")], small_registry)
    assert out["status"] == "answered" and [c["node"] for c in ctx.calls] == ["planner", "step.agent", "synth"]


def test_plan_is_capped_at_three_steps(small_registry):
    steps = '{"steps": ["1", "2", "3", "4", "5"]}'
    out, ctx, _, _ = run("plan_execute", [say(steps), say("r1"), say("r2"), say("r3"), say("final")], small_registry)
    assert [c["node"] for c in ctx.calls].count("step.agent") == 3


# ---- C: supervisor ------------------------------------------------------------------------------------
def test_supervisor_researches_then_hands_to_the_writer(small_registry):
    script = [say('{"next": "researcher", "task": "find the article"}'), tool_call("get_article", law="民法", article="5"), say("found: id 5"),
              say('{"next": "writer", "task": ""}'), say("民法第五条です。")]
    out, ctx, _, lt = run("supervisor", script, small_registry)
    assert out["status"] == "answered" and [c["node"] for c in ctx.calls] == ["supervisor", "researcher.agent", "researcher.agent", "supervisor", "writer"]
    assert score_answer(Q, out["answer"], lt)["correct"]


def test_supervisor_with_a_garbled_reply_defaults_to_the_researcher(small_registry):
    out, ctx, _, _ = run("supervisor", [say("hmm"), say("found: id 5"), say('{"next": "writer"}'), say("民法第五条")], small_registry)
    assert [c["node"] for c in ctx.calls] == ["supervisor", "researcher.agent", "supervisor", "writer"] and out["status"] == "answered"


def test_supervisor_is_forced_to_the_writer_after_three_research_rounds(small_registry):
    sup = say('{"next": "researcher", "task": "look more"}')
    out, ctx, _, _ = run("supervisor", [sup, say("r1"), sup, say("r2"), sup, say("r3"), say("final")], small_registry)
    nodes = [c["node"] for c in ctx.calls]
    assert nodes.count("supervisor") == 3 and nodes.count("researcher.agent") == 3 and nodes[-1] == "writer"


# ---- D: draft, verify, revise -------------------------------------------------------------------------
def test_a_valid_draft_is_not_revised(small_registry):
    out, ctx, _, _ = run("draft_verify", [say("民法第五条です。")], small_registry)
    assert out["status"] == "answered" and len(ctx.calls) == 1 and ctx.verify_log == [{"cited": ["5"], "invalid": []}]


def test_an_invented_citation_triggers_a_revision(small_registry):
    out, ctx, llm, lt = run("draft_verify", [say("民法第九十九条です。"), say("民法第五条です。")], small_registry)
    assert [c["node"] for c in ctx.calls] == ["draft.agent", "revise.agent"] and [v["invalid"] for v in ctx.verify_log] == [["99"], []]
    assert "do not exist in 民法: 99" in llm.seen[1][-1].content and score_answer(Q, out["answer"], lt)["correct"]


def test_an_answer_without_a_citation_is_revised(small_registry):
    out, ctx, llm, _ = run("draft_verify", [say("該当する条文があります。"), say("民法第五条です。")], small_registry)
    assert "cites no article number" in llm.seen[1][-1].content and out["answer"] == "民法第五条です。"


def test_revisions_are_bounded_and_the_last_draft_is_returned(small_registry):
    bad = lambda: say("民法第九十九条です。")
    out, ctx, _, lt = run("draft_verify", [bad(), bad(), bad()], small_registry)
    assert [c["node"] for c in ctx.calls] == ["draft.agent", "revise.agent", "revise.agent"] and len(ctx.verify_log) == 3
    assert score_answer(Q, out["answer"], lt)["invalid"] == ["99"]                       # retries exhausted: the invented citation is still scored


def test_every_architecture_name_builds(small_registry):
    for name in graphs.ARCHITECTURES:
        assert graphs.build_architecture(name, FakeChat([]), LawTools(small_registry)) is not None
