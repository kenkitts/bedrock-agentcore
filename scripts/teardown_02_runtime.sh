#!/usr/bin/env bash
#
# Teardown for Post 2 (Runtime).
#
# AgentCore Runtime is consumption-priced: an idle deployed agent costs little,
# but it is not free, and the ECR image + supporting resources linger until you
# remove them. This script removes everything the AgentCore CLI provisioned for
# this project and applies the removal.
#
# Safe to re-run: if there is nothing to remove, the commands no-op.

set -euo pipefail

if ! command -v agentcore >/dev/null 2>&1; then
    echo "The AgentCore CLI is not installed (npm install -g @aws/agentcore)." >&2
    echo "Nothing to tear down via the CLI." >&2
    exit 0
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
