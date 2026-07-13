"""Connect the notes agent to its tools over AgentCore Gateway (Post 4).

Posts 1-3 gave the agent tools as in-process Python functions. Post 4 moves the
real notes tools behind an AgentCore Gateway, which exposes them as an MCP
server. The agent now *discovers* its tools over the network instead of
importing them - and, crucially, can't tell the difference. A tool is a tool.

Two things to know about the lifecycle:

* The MCP client owns a live connection. Tools are only callable while that
  connection is open, so callers must use it as a context manager
  (``with client:``) and build/run the agent *inside* that block. See app.py
  and main.py.
* ``list_tools_sync`` is paginated. :func:`list_gateway_tools` walks every page
  so the agent sees the whole toolset, not just the first page.

When no gateway is configured (``GATEWAY_URL`` empty), :func:`build_gateway_client`
returns ``None`` and callers fall back to the local Post 1 tools - so the agent
still runs offline with no cloud dependency.

Post 5 (Identity): the gateway now requires a valid JWT for inbound auth
(``--authorizer-type CUSTOM_JWT``). The agent forwards the user's token on the
MCP connection so the gateway can validate it independently and the interceptor
can extract user identity for per-user scoping.
"""

from typing import Optional

from notes_agent.config import GATEWAY_URL


def _mcp_endpoint(url: str) -> str:
    """Ensure the gateway URL points at the MCP endpoint (``.../mcp``).

    ``agentcore status --json`` reports the gateway *host* without the ``/mcp``
    path (the plain ``agentcore status`` doesn't show the URL at all). A bare
    host answers MCP requests with an AgentCore service envelope rather than
    JSON-RPC, which Strands surfaces as an opaque "client initialization
    failed" error - hard to diagnose. Normalizing here means pasting either the
    host or the full ``/mcp`` URL into GATEWAY_URL both work.
    """
    trimmed = url.rstrip("/")
    return trimmed if trimmed.endswith("/mcp") else trimmed + "/mcp"


def build_gateway_client(token: Optional[str] = None):
    """Return an MCP client bound to the Gateway, or ``None`` if unconfigured.

    Imports are deferred so the package still imports cleanly when the optional
    ``mcp`` dependency isn't installed and no gateway is in use.

    Post 5 (Identity): when ``token`` is provided, it is sent as a Bearer token
    on the MCP HTTP connection. The Gateway's CUSTOM_JWT authorizer validates it
    independently, and the interceptor Lambda extracts the user's ``sub`` claim
    to inject into tool calls. When ``token`` is ``None`` (local REPL, no auth),
    no Authorization header is sent — works against a NONE-auth gateway or when
    the gateway is not configured.
    """
    if not GATEWAY_URL:
        return None

    from mcp.client.streamable_http import streamablehttp_client
    from strands.tools.mcp.mcp_client import MCPClient

    endpoint = _mcp_endpoint(GATEWAY_URL)
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return MCPClient(lambda: streamablehttp_client(endpoint, headers=headers))


def list_gateway_tools(client) -> list:
    """List every tool the gateway advertises, following pagination.

    Must be called inside ``with client:`` (an open MCP session).
    """
    tools: list = []
    pagination_token: Optional[str] = None
    while True:
        page = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(page)
        pagination_token = getattr(page, "pagination_token", None)
        if not pagination_token:
            return tools
