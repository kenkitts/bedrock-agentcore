# Building an Agent on Amazon Bedrock AgentCore

A hands-on, foundational blog series for **developers new to agents**. We build a
single research / notes assistant with [Strands Agents](https://strandsagents.com)
and grow it across the series, adding one Amazon Bedrock AgentCore capability per post.

> AWS fundamentals (IAM, deploying to the cloud) are assumed. The foundations
> taught here are *agent* and *AgentCore* concepts.

## The running example

A notes/research assistant. Each post gives it a new ability:

| Post | Tag | AgentCore primitive | What the agent gains |
|------|-----|---------------------|----------------------|
| 1. Foundations | `post-01-foundations` | — (local only) | It exists: a Strands agent with in-memory note tools, running locally |
| 2. Runtime | `post-02-runtime` | Runtime | It runs in the cloud |
| 3. Memory | `post-03-memory` | Memory | It remembers the conversation, then your preferences across sessions |
| 4. Gateway | `post-04-gateway` | Gateway | Real tools: a notes/bookmarks API exposed as MCP tools |
| 5. Identity | `post-05-identity` | Identity | "Your" notes vs. someone else's; governed tool calls |
| 6. Built-in tools | `post-06-builtin-tools` | Code Interpreter + Browser | Runs code to analyze notes; reads a live web page |
| 7. Observability | `post-07-observability` | Observability | Tracing, metrics, and evaluation |
| 8. (optional) What's next | `post-08-preview` | Policy / Evaluations (Preview) | Forward-looking preview features |

Each post links its cumulative tag and the **diff from the previous tag** — the diff is the lesson.

## Repo conventions

- **One repo, one git tag per post.** `git checkout post-03-memory` gives you the agent at that stage.
- **Config is centralized** in [`src/notes_agent/config.py`](src/notes_agent/config.py): `MODEL_ID` and `REGION` live there so a reader can swap them in one place.
- **Region:** `us-east-1` throughout (broadest AgentCore + Bedrock availability).
- **Cost:** every post has a "Prerequisites + cost" callout and a "Clean up" step. AgentCore is consumption-priced — idle resources cost little but non-zero.

## Prerequisites

- Python 3.10+
- An AWS account with **Amazon Bedrock model access enabled** for a Claude (Sonnet-class) model in `us-east-1` (see `config.py`).
- AWS credentials configured (`aws configure` or SSO).
- From Post 2 onward: the [AgentCore CLI](https://github.com/aws/agentcore-cli) — `npm install -g @aws/agentcore`.

## Quick start (Post 1, local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m notes_agent.main        # interactive local REPL
```

## Post 2 (Runtime): run in the cloud

The agent is unchanged; `app.py` wraps it in an AgentCore Runtime entrypoint.

Test the Runtime server locally first (starts `POST /invocations` on :8080):

```bash
python app.py                     # or: agentcore dev   (hot reload)
```

Deploy and invoke with the [AgentCore CLI](https://github.com/aws/agentcore-cli):

```bash
npm install -g @aws/agentcore
agentcore create --name notes-agent --no-agent
agentcore add agent --name notesAgent --type byo \
    --code-location . --entrypoint app.py --language Python
agentcore deploy -y
agentcore invoke "remember that runtime is post 2"
agentcore logs --follow           # watch it run
```

Clean up when done (see the per-post teardown note below):

```bash
scripts/teardown_02_runtime.sh
```

See [`PLAN.md`](PLAN.md) for the full series design and [`POST_TEMPLATE.md`](POST_TEMPLATE.md) for the post structure.
