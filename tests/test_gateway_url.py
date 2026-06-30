"""Unit tests for the gateway URL normalizer (Post 4).

Covers the exact deploy-time gotcha: `agentcore status` reports the gateway
host without the `/mcp` path, and a bare host answers with a non-MCP envelope.
``_mcp_endpoint`` normalizes either form to the MCP endpoint. This imports
notes_agent.gateway, whose mcp/strands imports are deferred, so the test runs
without the optional ``mcp`` dependency installed.
"""

from notes_agent.gateway import _mcp_endpoint

HOST = "https://gw-abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com"


def test_appends_mcp_to_bare_host():
    assert _mcp_endpoint(HOST) == HOST + "/mcp"


def test_leaves_existing_mcp_path_untouched():
    assert _mcp_endpoint(HOST + "/mcp") == HOST + "/mcp"


def test_strips_trailing_slash_before_appending():
    assert _mcp_endpoint(HOST + "/") == HOST + "/mcp"


def test_strips_trailing_slash_after_mcp():
    assert _mcp_endpoint(HOST + "/mcp/") == HOST + "/mcp"
