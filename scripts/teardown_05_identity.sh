#!/usr/bin/env bash
#
# Teardown for Post 5 (Identity).
#
# Post 5 adds three resources beyond what Posts 2-4 created:
#   1. A Cognito User Pool        (NotesAgentUserPool) — includes the app
#                                   client and demo users (cascaded on delete)
#   2. An interceptor Lambda       (NotesAgentInterceptor)
#   3. An IAM role for the above   (NotesAgentInterceptorRole)
#
# The Gateway's JWT authorizer config, the Runtime's JWT mode, and the
# DynamoDB table schema change are part of the deploy project and the
# create_notes_backend.py script respectively — handled by their own teardowns.
#
# Usage (from the repo root):
#   scripts/teardown_05_identity.sh

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
POOL_NAME="NotesAgentUserPool"
INTERCEPTOR_FUNCTION="NotesAgentInterceptor"
INTERCEPTOR_ROLE="NotesAgentInterceptorRole"
BASIC_EXEC_ARN="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

# --- Cognito User Pool -----------------------------------------------------
echo "Finding Cognito User Pool '${POOL_NAME}'..."
POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region "$REGION" \
    --query "UserPools[?Name=='${POOL_NAME}'].Id | [0]" --output text 2>/dev/null || echo "None")

if [ "$POOL_ID" != "None" ] && [ -n "$POOL_ID" ]; then
    echo "Deleting User Pool ${POOL_ID}..."
    aws cognito-idp delete-user-pool --user-pool-id "$POOL_ID" --region "$REGION"
    echo "  Done."
else
    echo "  (not found - skipping)"
fi

# --- Interceptor Lambda ----------------------------------------------------
echo "Deleting Lambda function ${INTERCEPTOR_FUNCTION}..."
aws lambda delete-function --function-name "$INTERCEPTOR_FUNCTION" --region "$REGION" 2>/dev/null \
    || echo "  (not found - skipping)"

# --- Interceptor IAM role --------------------------------------------------
echo "Detaching policies and deleting role ${INTERCEPTOR_ROLE}..."
aws iam detach-role-policy --role-name "$INTERCEPTOR_ROLE" --policy-arn "$BASIC_EXEC_ARN" 2>/dev/null || true
aws iam delete-role --role-name "$INTERCEPTOR_ROLE" 2>/dev/null \
    || echo "  (role not found - skipping)"

echo
echo "Identity resources removed."
echo
echo "Now tear down the Gateway backend + Runtime (from Posts 4/3/2):"
echo "    ~/bedrock-agentcore/scripts/teardown_04_gateway.sh"
echo "    ~/bedrock-agentcore/scripts/teardown_03_memory.sh <memory-id>"
echo "    cd ../notesAgentRuntime && ~/bedrock-agentcore/scripts/teardown_02_runtime.sh"
