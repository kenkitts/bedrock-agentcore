"""Local interactive REPL for the notes agent.

Run with:  python -m notes_agent.main

Post 3: if a Memory resource is configured (config.py MEMORY_ID, or the
NOTES_AGENT_MEMORY_ID env var), the REPL wires the agent to AgentCore Memory.

Post 4: if a Gateway is configured (config.py GATEWAY_URL, or the
NOTES_AGENT_GATEWAY_URL env var), the REPL discovers the notes tools over MCP
from the gateway instead of using the in-process ones. The MCP connection has
to stay open for the whole session, so the REPL loop runs inside ``with
mcp_client:``.

Post 5: if NOTES_AGENT_USER_ID is set, the REPL uses it as the actor_id for
Memory (per-user long-term memory) and mentions it in the system prompt. This
is the "graceful degradation" pattern: no JWT, no Gateway auth — just set a
user id directly for local iteration.

With neither configured, this is the memoryless Post 1 agent with local,
in-process tools - no AWS, no surprises.
"""

import os
import uuid

from notes_agent.agent import build_agent, SYSTEM_PROMPT
from notes_agent.config import GATEWAY_URL, MEMORY_ID
from notes_agent.gateway import build_gateway_client, list_gateway_tools
from notes_agent.memory import build_session_manager


def _repl(agent) -> None:
    """Read-eval-print loop against an already-built agent."""
    while True:
        try:
            prompt = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if prompt.lower() in {"exit", "quit"}:
            break
        if not prompt:
            continue
        # Calling the agent runs the loop: the model may call tools, observe
        # results, and loop until it produces a final answer.
        result = agent(prompt)
        print(f"agent> {result}\n")


def main() -> None:
    session_id = "local-" + uuid.uuid4().hex

    # Post 5: local REPL identity. No JWT needed — just set the env var.
    user_id = os.environ.get("NOTES_AGENT_USER_ID", "")
    actor_id = user_id or None  # None falls back to config.ACTOR_ID default

    session_manager = build_session_manager(session_id=session_id, actor_id=actor_id)

    # Build system prompt with identity context (if set).
    system_prompt = SYSTEM_PROMPT
    if user_id:
        system_prompt += f"\n\nThe authenticated user is {user_id}."

    memory = "on" if MEMORY_ID else "off"
    tools = "gateway" if GATEWAY_URL else "local"
    identity = user_id or "anonymous"
    print(
        f"Notes assistant (local, memory {memory}, tools {tools}, user {identity}). "
        "Type 'exit' or Ctrl-D to quit.\n"
    )

    mcp_client = build_gateway_client()
    try:
        if mcp_client is None:
            agent = build_agent(session_manager=session_manager, system_prompt=system_prompt)
            _repl(agent)
        else:
            # Tools are discovered over MCP; the connection stays open for the
            # whole REPL session.
            with mcp_client:
                gateway_tools = list_gateway_tools(mcp_client)
                agent = build_agent(
                    session_manager=session_manager,
                    tools=gateway_tools,
                    system_prompt=system_prompt,
                )
                _repl(agent)
    finally:
        if session_manager is not None:
            session_manager.close()


if __name__ == "__main__":
    main()
