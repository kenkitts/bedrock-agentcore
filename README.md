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

## Post 4 (Gateway): real tools behind an MCP endpoint

The notes finally get a durable home. Instead of an in-process Python list,
`add_note` / `list_notes` / `search_notes` are backed by a **DynamoDB table**
behind a **Lambda**, exposed to the agent as **MCP tools** through an
**AgentCore Gateway**. The agent discovers its tools over the network and can't
tell them from local ones.

Provision the backend **once** (DynamoDB table + Lambda + a least-privilege
execution role). We use a small SDK script rather than the CLI because we own
the Lambda's data-plane permissions:

```bash
pip install -r requirements.txt
python scripts/create_notes_backend.py   # prints NOTES_AGENT_BACKEND_LAMBDA_ARN=<arn>
```

Deploy the agent with the same BYO flow as Posts 2-3, then attach a gateway and
register the Lambda as a target with our tool schema:

```bash
cd ..
agentcore create --project-name notesAgentRuntime --no-agent
cd notesAgentRuntime
agentcore add agent --name notesAgent --type byo \
    --framework Strands --model-provider Bedrock --memory none \
    --code-location ../bedrock-agentcore --entrypoint app.py --language Python

# A gateway with NONE inbound auth (see the security note below), wired to the agent.
agentcore add gateway --name NotesGateway --authorizer-type NONE --runtimes notesAgent

# The Lambda target + the tool schema the model reads.
agentcore add gateway-target --name NotesTarget --type lambda-function-arn \
    --lambda-arn <NOTES_AGENT_BACKEND_LAMBDA_ARN> \
    --tool-schema-file ../bedrock-agentcore/scripts/notes_backend/tools.json \
    --gateway NotesGateway

agentcore deploy -y
agentcore status --json   # the Gateway URL lives in the JSON, not the plain output
```

**Record the Gateway URL so the agent can find it.** Like the Memory id, the
CLI can't inject env vars into the runtime, so paste the URL into
[`notes_agent/config.py`](notes_agent/config.py) (`GATEWAY_URL`) and
`agentcore deploy -y` once more so it ships with the bundled code. (Two-phase by
nature: the gateway doesn't exist until the first deploy.) The MCP endpoint is
the gateway host plus a `/mcp` path — `agentcore status --json` prints the host
(the plain `agentcore status` doesn't show the URL), and the bare host answers
with an AgentCore envelope instead of MCP, so the code appends `/mcp` for you if
you forget it. For local runs you can instead export it:

```bash
export NOTES_AGENT_GATEWAY_URL=<gateway-url>
python -m notes_agent.main          # local REPL, tools served by the gateway
```

> **Security note (paid off in Post 5).** `--authorizer-type NONE` means the
> gateway endpoint is **unauthenticated** — anyone with the URL can list and
> call your tools. That's a deliberate liability to keep this post focused on
> tools/MCP; **Post 5 (Identity)** locks it down with inbound auth and adds
> per-user scoping ("your notes vs. someone else's").

Tests start here — run the deterministic backend unit tests (no AWS):

```bash
pip install pytest
pytest
```

Clean up — Post 4 adds a DynamoDB table, a Lambda, and a role on top of the
Runtime/Memory:

```bash
# from the repo root (deletes the table, Lambda, and role, then prints the
# Gateway + Runtime teardown steps):
scripts/teardown_04_gateway.sh
```

## Post 5 (Identity): "your" notes vs. someone else's

Post 4 shipped an unauthenticated Gateway — anyone with the URL could call the
notes tools. Post 5 locks it down with **AgentCore Identity**: the Runtime and
Gateway both require a valid JWT, and the authenticated user's `sub` claim
flows through as `actor_id` for Memory and as per-user scoping for the notes
backend. The agent doesn't know or care what IdP issued the token — it just
reads a header; the infrastructure enforces identity.

We use **Amazon Cognito** as the identity provider (in-ecosystem, free tier,
no third-party signup).

**1. Provision Cognito** (User Pool + App Client + two demo users, `alice` and
`bob`) — run once:

```bash
pip install -r requirements.txt
python scripts/create_cognito.py
# prints:
#   NOTES_AGENT_COGNITO_POOL_ID=us-east-1_XXXXXXXXX
#   NOTES_AGENT_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
#   NOTES_AGENT_COGNITO_DISCOVERY_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXXX/.well-known/openid-configuration
export NOTES_AGENT_COGNITO_POOL_ID=<pool-id>
export NOTES_AGENT_COGNITO_CLIENT_ID=<client-id>
export NOTES_AGENT_COGNITO_DISCOVERY_URL=<discovery-url>
```

**2. Update the notes backend for per-user scoping.** Post 5 changes the
DynamoDB table to a composite key (`user_id` PK + `note_id` SK) so queries are
scoped to one user instead of scanning everyone's notes:

```bash
python scripts/create_notes_backend.py   # idempotent; updates the existing table/Lambda
```

**3. Deploy the agent and Gateway with JWT auth.** This is the same BYO flow as
Posts 2-4, but both the agent and the Gateway now take `--authorizer-type
CUSTOM_JWT` (with `--allowed-clients`, not `--allowed-audience` — Cognito access
tokens carry `client_id`, not `aud`):

```bash
cd ..
agentcore create --project-name notesAgentRuntime --no-agent
cd notesAgentRuntime

agentcore add agent --name notesAgent --type byo \
    --framework Strands --model-provider Bedrock --memory none \
    --code-location ../bedrock-agentcore --entrypoint app.py --language Python \
    --authorizer-type CUSTOM_JWT \
    --discovery-url "$NOTES_AGENT_COGNITO_DISCOVERY_URL" \
    --allowed-clients "$NOTES_AGENT_COGNITO_CLIENT_ID" \
    --request-header-allowlist "Authorization"

agentcore add gateway --name NotesGateway \
    --authorizer-type CUSTOM_JWT \
    --discovery-url "$NOTES_AGENT_COGNITO_DISCOVERY_URL" \
    --allowed-clients "$NOTES_AGENT_COGNITO_CLIENT_ID" \
    --runtimes notesAgent

agentcore add gateway-target --name NotesTarget --type lambda-function-arn \
    --lambda-arn "$NOTES_AGENT_BACKEND_LAMBDA_ARN" \
    --tool-schema-file ../bedrock-agentcore/scripts/notes_backend/tools.json \
    --gateway NotesGateway

agentcore deploy -y
agentcore status --json   # note the gateway id + gateway URL (host)
```

**4. Paste the Gateway URL into `config.py` — this step is easy to miss but
required.** Exactly like Post 4: the AgentCore CLI has no way to inject env
vars into the Runtime container, so the agent can't discover the Gateway URL
on its own. Take the URL from `agentcore status --json` (run in step 3) and
paste it into [`notes_agent/config.py`](notes_agent/config.py) (`GATEWAY_URL`),
then redeploy so it ships with the bundled code:

```bash
cd ../notesAgentRuntime
agentcore deploy -y
```

Without this step the agent falls back to the local Post 1 tools (`GATEWAY_URL`
empty) even though the Gateway is fully deployed — it will run, but every note
tool call stays in-process and never reaches the per-user DynamoDB-backed
backend, so `alice` and `bob` will silently share the same in-memory store
instead of getting isolated notes.

For local runs you can skip editing `config.py` and export the URL instead:

```bash
export NOTES_AGENT_GATEWAY_URL=<gateway-url>
```

**5. Attach the identity interceptor and grant the Gateway invoke permissions.**
The `Authorization` header can't be forwarded to a Lambda target via the
Gateway's header allowlist — only an interceptor Lambda can extract claims from
it. The AgentCore CLI has no flag for this, so it's wired post-deploy via the
SDK. The CLI-generated Gateway role also ships with zero policies, so grant it
explicitly (a silent 500 with no Lambda logs is the symptom if you skip this):

```bash
python scripts/create_interceptor.py
# prints: NOTES_AGENT_INTERCEPTOR_LAMBDA_ARN=<arn>

python scripts/attach_interceptor.py <gateway-id> <interceptor-lambda-arn>

# gateway-id and gateway-role-name: from `agentcore status --json`
aws iam put-role-policy --role-name <gateway-role-name> --policy-name GatewayInvokeLambdas \
    --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"lambda:InvokeFunction","Resource":["<interceptor-arn>","<notes-backend-lambda-arn>"]}]}'
```

> **Redeploys can reset this.** `agentcore deploy -y` may recreate the Gateway
> and wipe both the interceptor attachment and the inline role policy above.
> After any redeploy, re-run `attach_interceptor.py` and re-run the
> `put-role-policy` command.

**6. Mint tokens and see per-user isolation.** `get_token.py` authenticates a
demo user against Cognito with zero browser interaction (access tokens expire
after 1 hour — just re-run it):

```bash
# Rejected — no token:
agentcore invoke "hello"        # 401/403

# Alice adds and lists her own notes:
eval "$(python scripts/get_token.py alice)"
agentcore invoke --bearer-token "$NOTES_AGENT_TOKEN" "add a note: meeting at 3pm"
agentcore invoke --bearer-token "$NOTES_AGENT_TOKEN" "list my notes"

# Bob sees his own (empty) list — not Alice's:
eval "$(python scripts/get_token.py bob)"
agentcore invoke --bearer-token "$NOTES_AGENT_TOKEN" "list my notes"   # "No notes yet."
```

For the local REPL without a JWT, set the user id directly (graceful
degradation — no Cognito round trip needed for local iteration):

```bash
export NOTES_AGENT_USER_ID=alice
python -m notes_agent.main
```

Run the extended per-user isolation tests (no AWS):

```bash
pytest
```

Clean up — Post 5 adds a Cognito User Pool, an interceptor Lambda, and its IAM
role on top of Posts 2-4's resources:

```bash
# from the repo root (deletes the Cognito pool, interceptor Lambda, and role,
# then prints the Gateway/Memory/Runtime teardown steps):
scripts/teardown_05_identity.sh
```

See [`PLAN.md`](PLAN.md) for the full series design and [`POST_TEMPLATE.md`](POST_TEMPLATE.md) for the post structure.
