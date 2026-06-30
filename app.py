"""AgentCore Runtime entrypoint for the notes agent.

Post 2 introduced this file to host the agent in the cloud. Post 3 (Memory)
changes one thing: instead of a single module-load agent, we build a
*session-scoped* agent per invocation, bound to that session's AgentCore
Memory. Memory is session-specific, so Post 2's "build once and reuse"
optimization no longer fits — the agent is constructed per request.

``BedrockAgentCoreApp`` turns the decorated handler into an HTTP server
(``POST /invocations`` on port 8080) that AgentCore Runtime hosts. Locally,
``python app.py`` starts that same server.

Deploy with the AgentCore CLI (``npm install -g @aws/agentcore``). First
provision the Memory resource and record its id in notes_agent/config.py
(see scripts/create_memory.py), then deploy the agent as bring-your-own-code:

    cd ..
    agentcore create --project-name notesAgentRuntime --no-agent
    cd notesAgentRuntime
    agentcore add agent --name notesAgent --type byo \
        --framework Strands --model-provider Bedrock --memory none \
        --code-location ../bedrock-agentcore --entrypoint app.py --language Python
    agentcore deploy -y
    # Reuse one session id (33+ chars) to get conversation continuity:
    agentcore invoke --session-id notes-demo-session-0001-aaaaaaaaaaaa \
        "remember I like terse, bullet-point summaries"

(``--memory none`` refers to the CLI's managed-memory option; we provision and
wire our own Memory resource in code, so we leave the CLI's off.)
"""

import uuid

from bedrock_agentcore import BedrockAgentCoreApp

from notes_agent.agent import build_agent
from notes_agent.gateway import build_gateway_client, list_gateway_tools
from notes_agent.memory import build_session_manager

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """Handle one Runtime invocation, scoped to its session's memory.

    AgentCore passes the request body as ``payload`` and request metadata as
    ``context``. We use ``context.session_id`` (the Runtime session, from the
    X-Amzn-Bedrock-AgentCore-Runtime-Session-Id header) as the memory session
    id so conversation memory lines up with the Runtime session. A plain local
    curl has no session header, so we fall back to a random id.
    """
    prompt = payload.get("prompt", "")
    session_id = getattr(context, "session_id", None) or uuid.uuid4().hex
    actor_id = payload.get("actor_id")  # optional; defaults to config.ACTOR_ID

    # build_session_manager returns None when no MEMORY_ID is configured, so
    # this gracefully degrades to the memoryless Post 2 agent.
    session_manager = build_session_manager(session_id=session_id, actor_id=actor_id)

    # build_gateway_client returns None when no GATEWAY_URL is configured, so
    # the agent falls back to the in-process Post 1 tools.
    mcp_client = build_gateway_client()
    if mcp_client is None:
        agent = build_agent(session_manager=session_manager)
        return {"result": str(agent(prompt))}

    # Gateway configured: tools are discovered over MCP, and the connection has
    # to stay open while the agent runs - so we build and call the agent inside
    # the `with` block.
    with mcp_client:
        tools = list_gateway_tools(mcp_client)
        agent = build_agent(session_manager=session_manager, tools=tools)
        return {"result": str(agent(prompt))}


if __name__ == "__main__":
    app.run()
