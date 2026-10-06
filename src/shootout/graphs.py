"""The four architectures, as LangGraph graphs over the same tools, prompts and budget.

  A react          one tool-using agent loop
  B plan_execute   a planner writes up to 3 steps, an executor runs each step as a small agent loop, a synthesizer writes the answer
  C supervisor     a supervisor routes between a researcher (agent loop) and a writer
  D draft_verify   a draft (agent loop), then a SYMBOLIC check of every citation against the registry, then up to 2 revisions
Every model call goes through `RunCtx.call`, so tokens and calls are counted per node and the budget applies equally. Nodes never raise on a bad model reply: a malformed
plan or routing reply falls back to a fixed default and is counted.
"""
import json
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from . import prompts as P
from .llm import clean
from .scoring import cited_ids
from .tools import make_tools

ARCHITECTURES = ("react", "plan_execute", "supervisor", "draft_verify")
MAX_ITERS = {"react": 8, "step": 4, "researcher": 4, "draft": 8, "revise": 5}
MAX_STEPS, MAX_RESEARCH, MAX_REVISIONS = 3, 3, 2
FAIL_PREFIXES = ("No such article", "INVALID", "Unknown law", "Tool error", "Unknown tool")


class ArchState(TypedDict, total=False):
    question: str
    law: str
    answer: str
    status: str                 # "" while running; "answered" | "budget_exhausted" | "llm_error" | "no_answer" when the run ends
    plan: list
    step: int
    findings: list
    task: str
    rounds: int
    draft: str
    problem: str
    revisions: int


class ReactState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    iters: int
    stop: str


def _ctx(config):
    return config["configurable"]["ctx"]


def _text(msg):
    return clean(msg.content if isinstance(msg.content, str) else str(msg.content))


def parse_json(text):
    """First JSON object in a reply, or None."""
    m = re.search(r"\{.*\}", clean(text), re.S)
    if not m:
        return None
    try:
        v = json.loads(m.group(0))
        return v if isinstance(v, dict) else None
    except json.JSONDecodeError:
        return None


# -- the agent loop shared by every architecture ---------------------------------------------------------
def build_react(llm, lt, name, max_iters):
    tools = make_tools(lt)
    tool_map = {t.name: t for t in tools}
    bound = llm.bind_tools(tools)

    def agent(state, config):
        msg = _ctx(config).call(f"{name}.agent", bound, state["messages"])
        if msg is None:
            return {"stop": "budget_or_error"}
        return {"messages": [msg], "iters": state.get("iters", 0) + 1}

    def run_tools(state, config):
        ctx, out = _ctx(config), []
        for tc in state["messages"][-1].tool_calls:
            fn = tool_map.get(tc["name"])
            try:
                res = str(fn.invoke(tc["args"])) if fn else f"Unknown tool {tc['name']!r}"
            except Exception as e:                                       # noqa: BLE001  (bad arguments from the model are a tool failure, not a crash)
                res = f"Tool error: {type(e).__name__}"
            ctx.tool_calls.append({"node": name, "name": tc["name"], "args": tc["args"], "ok": not res.startswith(FAIL_PREFIXES)})
            out.append(ToolMessage(content=res, tool_call_id=tc["id"], name=tc["name"]))
        return {"messages": out}

    def force(state, config):
        msg = _ctx(config).call(f"{name}.force", llm, state["messages"] + [HumanMessage(content=P.FORCE_ANSWER)])
        return {"messages": [msg]} if msg is not None else {"stop": "budget_or_error"}

    def after_agent(state):
        if state.get("stop"):
            return END
        last = state["messages"][-1]
        return "tools" if isinstance(last, AIMessage) and last.tool_calls else END

    def after_tools(state):
        return "force" if state.get("iters", 0) >= max_iters else "agent"

    g = StateGraph(ReactState)
    g.add_node("agent", agent)
    g.add_node("tools", run_tools)
    g.add_node("force", force)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", after_agent, {"tools": "tools", END: END})
    g.add_conditional_edges("tools", after_tools, {"force": "force", "agent": "agent"})
    g.add_edge("force", END)
    return g.compile(name=f"react-{name}")


def run_react(react, system, user, config):
    """Run an agent loop and return its final text ('' if it produced none)."""
    out = react.invoke({"messages": [SystemMessage(content=system), HumanMessage(content=user)]}, {**config, "recursion_limit": 60})
    for m in reversed(out["messages"]):
        if isinstance(m, AIMessage) and not m.tool_calls and _text(m):
            return _text(m)
    return ""


def _findings(items):
    return "\n".join(f"- {t[:500]}" for t in items) if items else "(none yet)"


def _end_if_done(nxt):
    return lambda s: END if s.get("status") else nxt


def _finish(text, ctx):
    """Final status of a run from its last text."""
    if text:
        return {"answer": text, "status": "answered"}
    return {"answer": "", "status": "budget_exhausted" if ctx.exhausted() else ("llm_error" if ctx.errors else "no_answer")}


# -- A: ReAct ----------------------------------------------------------------------------------------------
def build_react_arch(llm, lt):
    react = build_react(llm, lt, "react", MAX_ITERS["react"])

    def node(state, config):
        return _finish(run_react(react, P.BASE, state["question"], config), _ctx(config))

    g = StateGraph(ArchState)
    g.add_node("react", node)
    g.add_edge(START, "react")
    g.add_edge("react", END)
    return g.compile(name="A-react")


# -- B: plan and execute -----------------------------------------------------------------------------------
def build_plan_execute(llm, lt):
    react = build_react(llm, lt, "step", MAX_ITERS["step"])

    def planner(state, config):
        msg = _ctx(config).call("planner", llm, [SystemMessage(content=P.PLANNER), HumanMessage(content=state["question"])])
        if msg is None:
            return {"status": "budget_exhausted" if _ctx(config).exhausted() else "llm_error"}
        steps = (parse_json(_text(msg)) or {}).get("steps")
        steps = [str(s) for s in steps][:MAX_STEPS] if isinstance(steps, list) and steps else [state["question"]]
        return {"plan": steps, "step": 0, "findings": []}

    def executor(state, config):
        ctx = _ctx(config)
        text = run_react(react, P.BASE, P.STEP.format(question=state["question"], findings=_findings(state["findings"]), step=state["plan"][state["step"]]), config)
        return {"findings": state["findings"] + [text or "(no result)"], "step": state["step"] + 1}

    def after_executor(state):
        return "executor" if state["step"] < len(state["plan"]) else "synth"

    def synth(state, config):
        ctx = _ctx(config)
        msg = ctx.call("synth", llm, [HumanMessage(content=P.SYNTH.format(question=state["question"], findings=_findings(state["findings"])))])
        return _finish(_text(msg) if msg is not None else "", ctx)

    g = StateGraph(ArchState)
    g.add_node("planner", planner)
    g.add_node("executor", executor)
    g.add_node("synth", synth)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", _end_if_done("executor"), {"executor": "executor", END: END})
    g.add_conditional_edges("executor", after_executor, {"executor": "executor", "synth": "synth"})
    g.add_edge("synth", END)
    return g.compile(name="B-plan-execute")


# -- C: supervisor with researcher and writer --------------------------------------------------------------
def build_supervisor(llm, lt):
    react = build_react(llm, lt, "researcher", MAX_ITERS["researcher"])

    def supervisor(state, config):
        ctx, findings, rounds = _ctx(config), state.get("findings", []), state.get("rounds", 0)
        if rounds >= MAX_RESEARCH:
            return {"task": "", "rounds": rounds}
        msg = ctx.call("supervisor", llm, [HumanMessage(content=P.SUPERVISOR.format(question=state["question"], findings=_findings(findings)))])
        if msg is None:
            return {"status": "budget_exhausted" if ctx.exhausted() else "llm_error"}
        d = parse_json(_text(msg)) or {}
        task = str(d.get("task") or "").strip()
        if d.get("next") == "writer" and findings:
            return {"task": ""}
        return {"task": task or state["question"], "rounds": rounds + 1}

    def route(state):
        if state.get("status"):
            return END
        return "researcher" if state.get("task") else "writer"

    def researcher(state, config):
        text = run_react(react, P.BASE, P.RESEARCHER.format(question=state["question"], findings=_findings(state.get("findings", [])), step=state["task"]), config)
        return {"findings": state.get("findings", []) + [text or "(no result)"]}

    def writer(state, config):
        ctx = _ctx(config)
        msg = ctx.call("writer", llm, [HumanMessage(content=P.WRITER.format(question=state["question"], findings=_findings(state.get("findings", []))))])
        return _finish(_text(msg) if msg is not None else "", ctx)

    g = StateGraph(ArchState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher)
    g.add_node("writer", writer)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route, {"researcher": "researcher", "writer": "writer", END: END})
    g.add_edge("researcher", "supervisor")
    g.add_edge("writer", END)
    return g.compile(name="C-supervisor")


# -- D: draft, symbolic verification, revision -------------------------------------------------------------
def build_draft_verify(llm, lt):
    draft_agent = build_react(llm, lt, "draft", MAX_ITERS["draft"])
    revise_agent = build_react(llm, lt, "revise", MAX_ITERS["revise"])

    def draft(state, config):
        text = run_react(draft_agent, P.BASE, state["question"], config)
        return {"draft": text, "revisions": 0}

    def verify(state, config):
        ctx, law = _ctx(config), state["law"]
        cited = cited_ids(state.get("draft", ""))
        invalid = [c for c in cited if not lt.exists(law, c)]
        ctx.verify_log.append({"cited": cited, "invalid": invalid})
        problem = ""
        if not state.get("draft"):
            problem = "You gave no answer."
        elif not cited:
            problem = "Your answer cites no article number. Cite the article(s) by number."
        elif invalid:
            problem = f"These cited articles do not exist in {law}: {', '.join(invalid)}."
        return {"problem": problem}

    def after_verify(state, config=None):
        return "revise" if state["problem"] and state.get("revisions", 0) < MAX_REVISIONS else "finish"

    def revise(state, config):
        text = run_react(revise_agent, P.BASE, P.REVISE.format(question=state["question"], draft=state.get("draft", ""), problem=state["problem"]), config)
        return {"draft": text or state.get("draft", ""), "revisions": state.get("revisions", 0) + 1}

    def finish(state, config):
        return _finish(state.get("draft", ""), _ctx(config))

    g = StateGraph(ArchState)
    g.add_node("draft", draft)
    g.add_node("verify", verify)
    g.add_node("revise", revise)
    g.add_node("finish", finish)
    g.add_edge(START, "draft")
    g.add_edge("draft", "verify")
    g.add_conditional_edges("verify", after_verify, {"revise": "revise", "finish": "finish"})
    g.add_edge("revise", "verify")
    g.add_edge("finish", END)
    return g.compile(name="D-draft-verify")


BUILDERS = {"react": build_react_arch, "plan_execute": build_plan_execute, "supervisor": build_supervisor, "draft_verify": build_draft_verify}


def build_architecture(name, llm, lt):
    return BUILDERS[name](llm, lt)


def run_question(graph, q, ctx):
    """Run one question through a compiled architecture; returns the final state (answer, status) and leaves the accounting in `ctx`."""
    return graph.invoke({"question": q["question"], "law": q["law"], "status": ""}, {"configurable": {"ctx": ctx}, "recursion_limit": 80})
