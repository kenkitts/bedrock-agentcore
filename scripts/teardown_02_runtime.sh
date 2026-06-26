#!/usr/bin/env bash
#
# Teardown for Post 2 (Runtime).
#
# Run this FROM INSIDE the deploy project you created with `agentcore create`
# (e.g. ../notesAgentRuntime), not from the repo. That project holds the
# agentcore/ config and CDK stack the CLI uses to tear resources down.
#
# AgentCore Runtime is consumption-priced: an idle deployed agent costs little,
# but it is not free, and the ECR image + supporting resources linger until you
# remove them.
#
# Safe to re-run: if there is nothing to remove, the commands no-op.

set -euo pipefail

if ! command -v agentcore >/dev/null 2>&1; then
    echo "The AgentCore CLI is not installed (npm install -g @aws/agentcore)." >&2
    exit 0
fi

if [ ! -f "agentcore/agentcore.json" ]; then
    echo "No agentcore/agentcore.json in the current directory." >&2
    echo "cd into your deploy project (e.g. notesAgentRuntime) first, then re-run." >&2
    exit 1
fi

echo "Current AgentCore resources:"
agentcore status || true

echo
echo "Removing all project resources..."
agentcore remove all -y

echo
echo "Applying the removal (deploys the now-empty stack)..."
agentcore deploy -y

echo
echo "Done. Verify nothing remains:"
agentcore status || true
