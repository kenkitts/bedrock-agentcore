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
- **Config is centralized** in [`notes_agent/config.py`](notes_agent/config.py): `MODEL_ID` and `REGION` live there so a reader can swap them in one place.
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

Deploy with the [AgentCore CLI](https://github.com/aws/agentcore-cli). The CLI
is project-oriented and scaffolds its own directory, so we create a small
*deployment* project **next to** the repo that points back at our code (BYO).
Keeping it as a sibling (not inside the repo) means `--code-location` doesn't
try to package itself.

```bash
npm install -g @aws/agentcore

# Create the deploy project alongside the repo (alphanumeric name, no hyphens).
cd ..
agentcore create --project-name notesAgentRuntime --no-agent
cd notesAgentRuntime

# Register THIS repo's app.py as a bring-your-own-code agent.
agentcore add agent --name notesAgent --type byo \
    --framework Strands --model-provider Bedrock --memory none \
    --code-location ../bedrock-agentcore --entrypoint app.py --language Python

agentcore deploy -y
agentcore invoke "remember that runtime is post 2"
agentcore logs --follow           # watch it run
```

Clean up when done — run the teardown from inside the deploy project:

```bash
cd ../notesAgentRuntime
~/bedrock-agentcore/scripts/teardown_02_runtime.sh
```

## Post 3 (Memory): remember the conversation, then the user

Same agent, now wired to **AgentCore Memory**. `app.py` builds a per-session
agent so a conversation survives cold starts (short-term memory) and the agent
remembers your preferences and facts **across sessions** (long-term memory).

Provision the Memory resource **once**. We use a small SDK script rather than
`agentcore add memory` because the CLI can't set namespaces, and long-term
retrieval has to query those exact namespaces:

```bash
pip install -r requirements.txt
python scripts/create_memory.py        # prints: NOTES_AGENT_MEMORY_ID=<id>
```

Record the id so the agent can find it. The AgentCore CLI has no way to inject
environment variables into the runtime, so paste the id into
[`notes_agent/config.py`](notes_agent/config.py) (`MEMORY_ID`) — it ships with
the bundled code. For local runs you can instead export it:

```bash
export NOTES_AGENT_MEMORY_ID=<id>
python -m notes_agent.main             # local REPL, memory on
```

Deploy with the same CLI BYO flow as Post 2 (`--memory none` — we provision and
wire our own Memory resource in code, so the CLI's managed memory stays off):

```bash
cd ..
agentcore create --project-name notesAgentRuntime --no-agent
cd notesAgentRuntime
agentcore add agent --name notesAgent --type byo \
    --framework Strands --model-provider Bedrock --memory none \
    --code-location ../bedrock-agentcore --entrypoint app.py --language Python
agentcore deploy -y
```

**Grant the runtime access to the memory.** Because we deploy with `--memory
none`, the CLI-generated execution role has *no* Memory permissions — the agent
will authenticate but every memory call fails with `AccessDeniedException`. BYO
memory means you grant access too. Attach a least-privilege policy (the five
actions the session manager calls) scoped to your one memory resource:

```bash
# role name: see `agentcore status` in the deploy project, or the principal ARN
# in the AccessDeniedException the agent logs on its first memory call.
scripts/grant_memory_access.sh <execution-role-name> "$NOTES_AGENT_MEMORY_ID"
```

The policy itself is in [`scripts/memory-policy.json`](scripts/memory-policy.json).
IAM propagates in a few seconds; then invoke with a fresh session id.

See it remember across sessions — reuse one session id for a conversation, then
start a **new** session and watch long-term memory carry over (session ids must
be 33+ characters):

```bash
SID=notes-demo-session-0001-aaaaaaaaaaaa
agentcore invoke --session-id "$SID" "I prefer terse, bullet-point summaries"
agentcore invoke --session-id "$SID" "the Q3 planning doc is in the shared drive"
# A brand-new session — short-term context is gone, but long-term memory isn't:
agentcore invoke --session-id notes-demo-session-0002-bbbbbbbbbbbb \
    "how do I like my summaries, and where's the Q3 doc?"
```

Clean up — the Memory resource is billable and retains events until they expire,
so delete it along with the Runtime (tearing down the Runtime also removes the
execution role and the inline memory policy you attached above):

```bash
# from the repo root (deletes the Memory resource, then prints the Runtime step):
scripts/teardown_03_memory.sh <memory-id>
```

See [`PLAN.md`](PLAN.md) for the full series design and [`POST_TEMPLATE.md`](POST_TEMPLATE.md) for the post structure.
