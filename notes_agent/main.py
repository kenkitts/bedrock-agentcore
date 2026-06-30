"""Local interactive REPL for the notes agent.

Run with:  python -m notes_agent.main

Post 3: if a Memory resource is configured (config.py MEMORY_ID, or the
NOTES_AGENT_MEMORY_ID env var), the REPL wires the agent to AgentCore Memory.

Post 4: if a Gateway is configured (config.py GATEWAY_URL, or the
NOTES_AGENT_GATEWAY_URL env var), the REPL discovers the notes tools over MCP
from the gateway instead of using the in-process ones. The MCP connection has
to stay open for the whole session, so the REPL loop runs inside ``with
mcp_client:``.

With neither configured, this is the memoryless Post 1 agent with local,
in-process tools - no AWS, no surprises.
"""

import uuid

from notes_agent.agent import build_agent
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
    session_manager = build_session_manager(session_id=session_id)

    memory = "on" if MEMORY_ID else "off"
    tools = "gateway" if GATEWAY_URL else "local"
    print(
        f"Notes assistant (local, memory {memory}, tools {tools}). "
        "Type 'exit' or Ctrl-D to quit.\n"
    )

    mcp_client = build_gateway_client()
    try:
        if mcp_client is None:
            agent = build_agent(session_manager=session_manager)
            _repl(agent)
        else:
            # Tools are discovered over MCP; the connection stays open for the
            # whole REPL session.
            with mcp_client:
                gateway_tools = list_gateway_tools(mcp_client)
                agent = build_agent(session_manager=session_manager, tools=gateway_tools)
                _repl(agent)
    finally:
        if session_manager is not None:
            session_manager.close()


if __name__ == "__main__":
    main()
