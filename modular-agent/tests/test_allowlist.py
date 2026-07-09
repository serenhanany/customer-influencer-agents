"""Module 2 — allowlist filtering behaves correctly (no MCP stack needed)."""

from modular_agent.tools import filter_tools


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


def _tools(*names):
    return [_FakeTool(n) for n in names]


def test_star_keeps_everything():
    tools = _tools("login", "create_post", "like_post")
    kept = filter_tools(tools, "*")
    assert [t.name for t in kept] == ["login", "create_post", "like_post"]


def test_explicit_allowlist_filters():
    tools = _tools("login", "create_post", "like_post", "follow_user")
    kept = filter_tools(tools, ["login", "create_post"])
    assert sorted(t.name for t in kept) == ["create_post", "login"]


def test_unknown_allowlisted_name_is_ignored(caplog):
    tools = _tools("login", "create_post")
    kept = filter_tools(tools, ["login", "does_not_exist"])
    assert [t.name for t in kept] == ["login"]
