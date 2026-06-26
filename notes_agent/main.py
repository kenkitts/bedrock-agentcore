"""Local interactive REPL for the Post 1 notes agent.

Run with:  python -m notes_agent.main

This is the "running locally" experience. Post 2 wraps the same agent in an
AgentCore Runtime entrypoint so it runs in the cloud.
"""

from notes_agent.agent import build_agent


def main() -> None:
    agent = build_agent()
    print("Notes assistant (local). Type 'exit' or Ctrl-D to quit.\n")
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


if __name__ == "__main__":
    main()
