#!/usr/bin/env bash
#
# Grant the AgentCore Runtime execution role access to the BYO Memory resource.
#
# Why this is needed: we deploy with `--memory none` (we provision and wire our
# OWN Memory resource in code), so the CLI-generated execution role ships with
# ZERO Memory permissions. The agent then authenticates fine but every memory
# call fails with AccessDeniedException. This attaches a least-privilege inline
# policy scoped to the single memory resource — see scripts/memory-policy.json
# for the policy itself.
#
# Usage (from the repo root):
#   scripts/grant_memory_access.sh <execution-role-name> <memory-id>
#   # memory-id may also come from NOTES_AGENT_MEMORY_ID
#
# Find the execution role name from the deploy project (`agentcore status`) or
# from the principal ARN in the AccessDeniedException the agent logs on its
# first memory call (assumed-role/<ROLE_NAME>/...).

set -euo pipefail

ROLE_NAME="${1:-}"
MEMORY_ID="${2:-${NOTES_AGENT_MEMORY_ID:-}}"
REGION="${AWS_REGION:-us-east-1}"

if [ -z "$ROLE_NAME" ] || [ -z "$MEMORY_ID" ]; then
    echo "Usage: $0 <execution-role-name> <memory-id>" >&2
    echo "       (memory id may also come from NOTES_AGENT_MEMORY_ID)" >&2
    exit 1
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
MEMORY_ARN="arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:memory/${MEMORY_ID}"

echo "Granting role '${ROLE_NAME}' least-privilege access to: ${MEMORY_ARN}"

aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name NotesAgentMemoryAccess \
    --policy-document "$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NotesAgentMemoryAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateEvent",
        "bedrock-agentcore:GetEvent",
        "bedrock-agentcore:DeleteEvent",
        "bedrock-agentcore:ListEvents",
        "bedrock-agentcore:RetrieveMemoryRecords"
      ],
      "Resource": "${MEMORY_ARN}"
    }
  ]
}
JSON
)"

echo "Done. IAM propagates in a few seconds — re-run the invoke with a fresh --session-id."
echo "To reverse: aws iam delete-role-policy --role-name ${ROLE_NAME} --policy-name NotesAgentMemoryAccess"
