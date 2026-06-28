"""Local interactive REPL for the notes agent.

Run with:  python -m notes_agent.main

Post 3: if a Memory resource is configured (config.py MEMORY_ID, or the
NOTES_AGENT_MEMORY_ID env var), the REPL wires the agent to AgentCore Memory.
Each run uses a fresh session id, so *long-term* memory (preferences, facts)
carries across runs while the short-term conversation does not — which is
exactly how a brand-new cloud session behaves. Without a Memory resource, this
is the memoryless Post 1 agent.
"""

import uuid

from notes_agent.agent import build_agent
from notes_agent.config import MEMORY_ID
from notes_agent.memory import build_session_manager


def main() -> None:
    session_id = "local-" + uuid.uuid4().hex
    session_manager = build_session_manager(session_id=session_id)
    agent = build_agent(session_manager=session_manager)

    status = "on" if MEMORY_ID else "off"
    print(f"Notes assistant (local, memory {status}). Type 'exit' or Ctrl-D to quit.\n")
    try:
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
    finally:
        if session_manager is not None:
            session_manager.close()


if __name__ == "__main__":
    main()
