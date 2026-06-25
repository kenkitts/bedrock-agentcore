# Plan: Building an Agent on Amazon Bedrock AgentCore — An Educational Blog Series

A 7-post (plus 1 optional) foundational series. One notes/research assistant agent
that gains a new capability each post, built with Strands Agents and hosted on
Amazon Bedrock AgentCore.

## Audience

Working developers who are **new to agents**. AWS fundamentals (IAM, Lambda,
deploying to the cloud) are assumed known. The "foundations" being taught are
*agent* and *AgentCore* concepts — not cloud basics. Code examples can be
non-trivial without apology.

## Locked Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Audience | Working devs new to agents; AWS assumed known |
| 2 | Running example | A research / notes assistant that grows across the series |
| 3 | Framework | Strands Agents throughout |
| 4 | Language | Python |
| 5 | Model | Anthropic Claude (Sonnet-class), model ID isolated in one config constant; Nova noted once as cheaper AWS-native alternative |
| 6 | Series scope | 7 core posts (+ optional 8th on Preview features) |
| 7 | Repo structure | One repo, one git **tag per post**; each post links its cumulative tag + diff from the previous tag |
| 8 | Provisioning | AgentCore **CLI** (`@aws/agentcore`, `npm install -g @aws/agentcore`) + in-code SDK/boto3 calls for Memory/Gateway/Identity; CDK shown only in a "productionizing" appendix. (Originally chose the Python starter-toolkit CLI, but AWS deprecated it in favor of the AgentCore CLI — same intent: AWS-blessed CLI over CDK.) |
| 9 | Cost/teardown | Per-post "Prerequisites + rough cost" callout (top) and "Clean up" section (bottom), each backed by a teardown command at that tag |
| 10 | Post template | Standardized 9-part anatomy → `POST_TEMPLATE.md` |
| 11 | Testing | B-lite: unit-test deterministic tool/parsing code from the Gateway post onward; agent *evaluation* taught in the Observability post |
| 12 | Region | `us-east-1` (broadest AgentCore + Bedrock availability); region + model ID in the shared config block |

## Why This Example Works

The research/notes assistant maps every AgentCore primitive to an obvious,
motivated need, requires no paid third-party accounts, and keeps domain logic
near-zero so the lesson always stays in front:

- **Memory** → remembers what you've told it and your preferences
- **Gateway** → a simple notes/bookmarks API becomes callable tools
- **Identity** → "your" notes vs. someone else's
- **Code Interpreter** → analyze the data/notes you've collected
- **Browser** → fetch and read a live web page to add to your notes

## Post Template (`POST_TEMPLATE.md`)

Every post follows this 9-part anatomy:

1. **Hook / the problem** — what limitation of the previous post's agent does this solve?
2. **Concept** — what the primitive *is*, vendor-neutral, before any AWS specifics.
3. **How AgentCore does it** — the service and its key API/SDK surface.
4. **Prerequisites + rough cost** callout.
5. **Build it** — code, introduced as a diff from the previous tag.
6. **Run / see it work** — concrete demo with expected output.
7. **Under the hood** — the one or two mechanics worth demystifying.
8. **Clean up** — teardown.
9. **Recap + what's next** — link forward.

## Series Outline

### Post 1 — Foundations: What Is an Agent?
- **Primitive:** none yet (local only).
- **Agent gains:** existence — a Strands notes-agent running locally.
- **Learning objective:** the agent loop (model → tool call → execute → loop, à la
  Simon Willison's "an LLM agent runs tools in a loop to achieve a goal"), and where
  AgentCore fits.
- **Load-bearing section:** *Concept* — must explain the loop conceptually even though
  Strands implements it (we are not hand-rolling a raw loop).
- **Tests:** none yet.

### Post 2 — Runtime: Deploy to the Cloud
- **Primitive:** AgentCore Runtime.
- **Agent gains:** cloud hosting — same agent, now deployed via `agentcore launch`.
- **Learning objective:** packaging/containerizing an agent and serverless agent hosting.
- **Load-bearing section:** *How AgentCore does it* + *Under the hood* (ECR/container, the harness).

### Post 3 — Memory: Short- and Long-Term
- **Primitive:** AgentCore Memory.
- **Agent gains:** remembers the conversation, then remembers preferences/facts across sessions.
- **Learning objective:** short-term vs. long-term memory; how memory is stored/retrieved.
- **Load-bearing section:** *Build it* (wiring memory) + *Run* (show it remembering).

### Post 4 — Gateway: Tools as a Service
- **Primitive:** AgentCore Gateway.
- **Agent gains:** real tools — a notes/bookmarks API exposed as MCP tools.
- **Learning objective:** turning APIs into governed tools; MCP.
- **Load-bearing section:** *Build it*.
- **Tests start here:** unit-test the deterministic notes/bookmarks tool functions and parsing.

### Post 5 — Identity: Who's Asking?
- **Primitive:** AgentCore Identity.
- **Agent gains:** per-user scoping — "your notes vs. someone else's"; inbound auth.
- **Learning objective:** agent identity, scoped access, governed tool calls.
- **Load-bearing section:** *Concept* + *Under the hood*.

### Post 6 — Built-in Tools: Code Interpreter + Browser
- **Primitive:** AgentCore Code Interpreter + Browser.
- **Agent gains:** runs code to analyze collected notes; fetches and reads a live web page.
- **Learning objective:** sandboxed code execution and managed browsing as first-class tools.
- **Load-bearing section:** *Run / see it work* (two concrete demos).

### Post 7 — Observability: Trace and Evaluate
- **Primitive:** AgentCore Observability.
- **Agent gains:** visibility — tracing, metrics, dashboards (CloudWatch / OpenTelemetry).
- **Learning objective:** end-to-end tracing, operational metrics, and **agent evaluation**
  (where behavior testing belongs).
- **Load-bearing section:** *Run* (reading traces) + the evaluation discussion.

### Post 8 (optional) — What's Next: Preview Features
- **Primitive:** AgentCore Policy (Preview), Evaluations (Preview).
- **Note:** treated as forward-looking; preview APIs may change, so kept out of the core path.

## Repository Layout

```
bedrock-agentcore/
  PLAN.md                 # this file
  POST_TEMPLATE.md        # the 9-part anatomy
  README.md               # series intro + table: post -> tag -> what's new
  src/                    # the evolving agent (single source of truth)
  config.py               # MODEL_ID + REGION (us-east-1) isolated here
  tests/                  # deterministic unit tests (from Post 4 onward)
  scripts/teardown_*.sh   # per-post teardown
  appendix/cdk/           # "productionizing with CDK" appendix
```

- **Tags:** `post-01-foundations`, `post-02-runtime`, … `post-07-observability`.
- Each post links its cumulative tag and the diff from the previous tag (the diff *is* the lesson).
- README maintains a table mapping post → tag → what's new.
- **Maintenance cost accepted:** API changes/bug fixes may require refreshing downstream tags.

## Configuration (shared, isolated)

- `REGION = "us-east-1"`
- `MODEL_ID = "<current Claude Sonnet-class id>"` — **verify current and enable model
  access** in the account/region before Post 1; model IDs age out.

## Build Sequence (authoring order)

1. Scaffold repo: `README.md`, `POST_TEMPLATE.md`, `config.py`, `src/`, `tests/`, `scripts/`.
2. Build Post 1 agent locally (Strands + Bedrock), tag `post-01-foundations`.
3. Verify model access in `us-east-1`; confirm current Claude model ID.
4. For each subsequent post: implement the new capability as a diff, add per-post
   teardown, add tests where applicable, run/verify the demo, tag the post.
5. Write each post against the 9-part template, embedding the tag-to-tag diff.
6. Build the CDK "productionizing" appendix once the full agent exists.

## Cross-Cutting Responsibilities

- Every post: top "Prerequisites + rough cost" callout; bottom "Clean up" with a working teardown command.
- Note that AgentCore is consumption-priced — idle resources cost little but non-zero.
- Mention Nova once (Post 1 or 2) as the cheaper AWS-native model alternative.
- Security: each network-exposed/deployed step should call out the auth posture
  (especially Runtime in Post 2 and Identity in Post 5).
