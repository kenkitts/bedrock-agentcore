#!/usr/bin/env bash
#
# Teardown for Post 3 (Memory).
#
# Post 3 adds a second billable resource alongside the Runtime: the AgentCore
# Memory resource created by scripts/create_memory.py. Stored events expire only
# after the configured window, so delete the resource when you're done.
#
# There are two things to remove:
#   1. The Memory resource   (this script, via the SDK)
#   2. The Runtime           (scripts/teardown_02_runtime.sh, from the deploy project)
#
# Usage (from the repo root):
#   scripts/teardown_03_memory.sh <memory-id>
#   # or: NOTES_AGENT_MEMORY_ID=<id> scripts/teardown_03_memory.sh

set -euo pipefail

MEMORY_ID="${1:-${NOTES_AGENT_MEMORY_ID:-}}"
REGION="${AWS_REGION:-us-east-1}"

if [ -n "$MEMORY_ID" ]; then
    echo "Deleting Memory resource $MEMORY_ID in $REGION ..."
    AWS_REGION="$REGION" python3 - "$MEMORY_ID" <<'PY'
import os
import sys
from bedrock_agentcore.memory import MemoryClient

memory_id = sys.argv[1]
client = MemoryClient(region_name=os.environ.get("AWS_REGION") or None)
client.delete_memory_and_wait(memory_id)
print(f"Deleted memory {memory_id}.")
PY
else
    echo "No memory id provided (pass as arg or set NOTES_AGENT_MEMORY_ID)." >&2
    echo "Find it with:  python -c 'from bedrock_agentcore.memory import MemoryClient; print([m[\"id\"] for m in MemoryClient(region_name=\"'"$REGION"'\").list_memories()])'" >&2
fi

echo
echo "Memory done. Now tear down the Runtime from inside your deploy project:"
echo "    cd ../notesAgentRuntime && ~/bedrock-agentcore/scripts/teardown_02_runtime.sh"
