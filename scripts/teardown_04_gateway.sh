#!/usr/bin/env bash
#
# Teardown for Post 4 (Gateway).
#
# Post 4 adds three billable/standing resources beyond the Runtime and Memory:
#   1. A DynamoDB table   (NotesAgentNotes)
#   2. A Lambda function  (NotesAgentBackend)
#   3. An IAM role        (NotesAgentBackendRole)
# all created by scripts/create_notes_backend.py. This script removes them.
#
# The Gateway itself is part of your AgentCore deploy project (you added it with
# `agentcore add gateway`), so it comes down with the Runtime teardown - see the
# pointer at the end.
#
# Usage (from the repo root):
#   scripts/teardown_04_gateway.sh

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
TABLE_NAME="NotesAgentNotes"
FUNCTION_NAME="NotesAgentBackend"
ROLE_NAME="NotesAgentBackendRole"
DDB_POLICY="NotesAgentDynamoAccess"
BASIC_EXEC_ARN="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

echo "Deleting Lambda function $FUNCTION_NAME ..."
aws lambda delete-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null \
    || echo "  (not found - skipping)"

echo "Deleting DynamoDB table $TABLE_NAME ..."
aws dynamodb delete-table --table-name "$TABLE_NAME" --region "$REGION" >/dev/null 2>&1 \
    && echo "  (delete initiated)" \
    || echo "  (not found - skipping)"

echo "Detaching policies and deleting role $ROLE_NAME ..."
aws iam delete-role-policy --role-name "$ROLE_NAME" --policy-name "$DDB_POLICY" 2>/dev/null || true
aws iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$BASIC_EXEC_ARN" 2>/dev/null || true
aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null \
    || echo "  (role not found - skipping)"

echo
echo "Backend resources removed."
echo
echo "Now remove the Gateway from your deploy project and redeploy:"
echo "    cd ../notesAgentRuntime"
echo "    agentcore remove gateway --name NotesGateway && agentcore deploy -y"
echo
echo "Then tear down the Runtime (and Memory, if you ran Post 3):"
echo "    ~/bedrock-agentcore/scripts/teardown_02_runtime.sh   # from the deploy project"
echo "    ~/bedrock-agentcore/scripts/teardown_03_memory.sh <memory-id>   # from the repo root"
