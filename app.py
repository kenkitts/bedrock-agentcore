"""AgentCore Runtime entrypoint for the notes agent.

This is the only new code Part 2 needs. It does not change the agent — it
wraps the *same* ``build_agent()`` from Part 1 in an AgentCore Runtime app so
the agent can run in the cloud instead of a terminal on your laptop.

``BedrockAgentCoreApp`` turns the decorated handler into an HTTP server
(``POST /invocations`` on port 8080) that AgentCore Runtime knows how to host.
Locally, ``python app.py`` starts that same server so you can test before you
deploy.

Deploy with the AgentCore CLI (``npm install -g @aws/agentcore``):

    agentcore create --name notes-agent --no-agent
    agentcore add agent --name notesAgent --type byo \
        --code-location . --entrypoint app.py --language Python
    agentcore deploy -y
    agentcore invoke "remember that runtime is post 2"
"""

from bedrock_agentcore import BedrockAgentCoreApp

from notes_agent.agent import build_agent

app = BedrockAgentCoreApp()

# Build the agent once at module load so warm invocations reuse it instead of
# reconstructing the model client on every request.
agent = build_agent()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Handle one Runtime invocation.

    AgentCore delivers the request body as ``payload``. We pull the user's
    prompt out, run the agent loop, and return the final text. (You could
    instead make this ``async`` and ``yield`` from ``agent.stream_async`` to
    stream tokens back — we keep it synchronous here to stay focused on
    hosting, not streaming.)
    """
    prompt = payload.get("prompt", "")
    result = agent(prompt)
    return {"result": str(result)}


if __name__ == "__main__":
    app.run()
