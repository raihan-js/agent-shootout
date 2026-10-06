"""A scripted stand-in for the chat model: returns the next prepared reply for each call, so graph logic is tested with no server."""
from langchain_core.messages import AIMessage


def tool_call(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"c{abs(hash((name, tuple(args.items())))) % 10**6}", "type": "tool_call"}])


def say(text):
    return AIMessage(content=text)


class FakeChat:
    def __init__(self, script):
        self.script = list(script)
        self.seen = []                                    # the messages of every call, for assertions

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.seen.append(list(messages))
        if not self.script:
            raise AssertionError("the script ran out: the graph made more model calls than expected")
        m = self.script.pop(0)
        m = m(messages) if callable(m) else m
        text = m.content if isinstance(m.content, str) else ""
        m.usage_metadata = {"input_tokens": 100 + 5 * len(messages), "output_tokens": 10 + len(text) // 4, "total_tokens": 0}
        return m
