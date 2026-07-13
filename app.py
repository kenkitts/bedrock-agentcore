"""AgentCore Runtime entrypoint for the notes agent.

Post 2 introduced this file to host the agent in the cloud. Post 3 (Memory)
builds a session-scoped agent per invocation, bound to that session's AgentCore
Memory. Post 4 (Gateway) adds MCP tool discovery.

Post 5 (Identity) adds inbound authentication and per-user scoping:

* The Runtime is configured in JWT mode — it validates the user's Cognito token
  before the handler runs. The validated JWT is available in
  ``context.request_headers["Authorization"]``.
* The handler decodes the JWT (signature already verified by the Runtime) to
  extract the ``sub`` claim, which becomes:
  - the ``actor_id`` for Memory (per-user long-term memory),
  - context in the system prompt ("The authenticated user is ..."),
  - the Bearer token forwarded to the Gateway (so the Gateway validates it
    independently and the interceptor can inject identity into tool calls).

``BedrockAgentCoreApp`` turns the decorated handler into an HTTP server
(``POST /invocations`` on port 8080) that AgentCore Runtime hosts.

Deploy with the AgentCore CLI. Post 5 switches the Runtime to JWT auth mode
and the Gateway to CUSTOM_JWT (see README for the full deploy commands).
"""

import uuid

import jwt as pyjwt
from bedrock_agentcore import BedrockAgentCoreApp

from notes_agent.agent import build_agent, SYSTEM_PROMPT
from notes_agent.config import IDENTITY_HEADER
from notes_agent.gateway import build_gateway_client, list_gateway_tools
from notes_agent.memory import build_session_manager

app = BedrockAgentCoreApp()


def _extract_user_id(context) -> tuple[str, str]:
    """Extract the user's identity from the Runtime-validated JWT.

    Returns (user_id, raw_token). The Runtime has already validated the
    signature, so we decode without verification to read claims.

    Falls back to ("", "") when no valid JWT is present (e.g., local testing
    without auth, or Posts 1-4 mode).
    """
    try:
        headers = context.request_headers or {}
        auth_header = headers.get(IDENTITY_HEADER, "") or headers.get(
            IDENTITY_HEADER.lower(), ""
        )
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            claims = pyjwt.decode(token, options={"verify_signature": False})
            sub = claims.get("sub", "")
            if sub:
                return sub, token
    except Exception:
        pass
    return "", ""


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """Handle one Runtime invocation with per-user identity scoping.

    The JWT authorizer validates the token before this handler runs. We
    extract the ``sub`` claim to scope memory and tool calls per-user.
    """
    prompt = payload.get("prompt", "")
    session_id = getattr(context, "session_id", None) or uuid.uuid4().hex

    # --- Identity (Post 5) -------------------------------------------------
    user_id, raw_token = _extract_user_id(context)

    # Use the authenticated user as the memory actor. Falls back to the
    # config default ("demo-user") when no identity is present, preserving
    # backward compatibility with Posts 1-4.
    actor_id = user_id or payload.get("actor_id") or None

    # --- Memory (Post 3) ---------------------------------------------------
    session_manager = build_session_manager(session_id=session_id, actor_id=actor_id)

    # --- System prompt with identity context (Post 5) ----------------------
    system_prompt = SYSTEM_PROMPT
    if user_id:
        system_prompt += f"\n\nThe authenticated user is {user_id}."

    # --- Tools via Gateway (Post 4) ----------------------------------------
    # Forward the user's JWT so the Gateway validates it independently and the
    # interceptor can extract identity for per-user tool scoping.
    mcp_client = build_gateway_client(token=raw_token or None)
    if mcp_client is None:
        agent = build_agent(
            session_manager=session_manager,
            system_prompt=system_prompt,
        )
        return {"result": str(agent(prompt))}

    with mcp_client:
        tools = list_gateway_tools(mcp_client)
        agent = build_agent(
            session_manager=session_manager,
            tools=tools,
            system_prompt=system_prompt,
        )
        return {"result": str(agent(prompt))}


if __name__ == "__main__":
    app.run()
