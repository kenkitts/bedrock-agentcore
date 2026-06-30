#!/usr/bin/env python3
"""Provision the notes backend for Post 4 (run once).

Post 4 gives the notes a real, durable home. This script stands up the three
AWS pieces the Gateway target needs:

  1. A DynamoDB table   (NotesAgentNotes) - where notes actually live.
  2. An IAM role        (NotesAgentBackendRole) - the Lambda's execution role,
                         granted exactly the DynamoDB actions it calls.
  3. A Lambda function  (NotesAgentBackend) - the gateway target; its code is
                         scripts/notes_backend/{handler,notes_core}.py.

It prints the Lambda ARN, which you pass to the AgentCore CLI when you add the
gateway target:

    agentcore add gateway-target --name NotesTarget --type lambda-function-arn \\
        --lambda-arn <printed-arn> \\
        --tool-schema-file scripts/notes_backend/tools.json --gateway NotesGateway

Note on permissions (the recurring "BYO resource means BYO permissions" beat):
we grant the *Lambda's* role access to DynamoDB here, because we own that edge.
The other edge - the Gateway invoking the Lambda - is wired by the AgentCore
CLI when you add the target, so it is not our job.

Run from the repo root:

    python scripts/create_notes_backend.py

Requires AWS credentials with permissions to create DynamoDB tables, IAM roles,
and Lambda functions.
"""

import io
import json
import os
import sys
import time
import zipfile

# Put the repo root on the path so ``notes_agent.config`` resolves (same
# co-location trick the other scripts use).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from notes_agent.config import REGION  # noqa: E402

TABLE_NAME = "NotesAgentNotes"
ROLE_NAME = "NotesAgentBackendRole"
FUNCTION_NAME = "NotesAgentBackend"
HANDLER = "handler.lambda_handler"
RUNTIME = "python3.12"
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes_backend")

LAMBDA_TRUST = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def ensure_table(ddb) -> str:
    """Create the notes table if absent; return its ARN."""
    existing = ddb.meta.client.list_tables()["TableNames"]
    if TABLE_NAME in existing:
        log(f"Table {TABLE_NAME!r} already exists.")
        return ddb.Table(TABLE_NAME).table_arn

    log(f"Creating DynamoDB table {TABLE_NAME!r} (on-demand)...")
    table = ddb.create_table(
        TableName=TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
    )
    table.wait_until_exists()
    return table.table_arn


def ensure_role(iam, table_arn: str) -> str:
    """Create the Lambda execution role if absent; return its ARN.

    Least privilege: basic Lambda logging + exactly the two DynamoDB actions
    the handler calls (PutItem to save, Scan to list/search), scoped to the one
    table.
    """
    try:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(LAMBDA_TRUST),
            Description="Execution role for the notes agent Gateway backend Lambda (blog Post 4).",
        )
        role_arn = role["Role"]["Arn"]
        log(f"Created role {ROLE_NAME!r}.")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        log(f"Role {ROLE_NAME!r} already exists.")

    iam.attach_role_policy(
        RoleName=ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="NotesAgentDynamoAccess",
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["dynamodb:PutItem", "dynamodb:Scan"],
                        "Resource": table_arn,
                    }
                ],
            }
        ),
    )
    return role_arn


def _zip_backend() -> bytes:
    """Zip the handler + pure core into a deployment package (in memory)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in ("handler.py", "notes_core.py"):
            zf.write(os.path.join(BACKEND_DIR, fname), arcname=fname)
    return buf.getvalue()


def ensure_function(lam, role_arn: str) -> str:
    """Create or update the Lambda; return its ARN."""
    code = _zip_backend()
    env = {"Variables": {"NOTES_TABLE": TABLE_NAME}}

    try:
        fn = lam.get_function(FunctionName=FUNCTION_NAME)
        log(f"Function {FUNCTION_NAME!r} exists; updating code.")
        lam.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=code)
        return fn["Configuration"]["FunctionArn"]
    except lam.exceptions.ResourceNotFoundException:
        pass

    log(f"Creating Lambda {FUNCTION_NAME!r}...")
    # IAM role creation is eventually consistent; retry through the window where
    # Lambda can't yet see the new role.
    for attempt in range(10):
        try:
            fn = lam.create_function(
                FunctionName=FUNCTION_NAME,
                Runtime=RUNTIME,
                Role=role_arn,
                Handler=HANDLER,
                Code={"ZipFile": code},
                Environment=env,
                Timeout=30,
                Description="Notes agent Gateway target backend (blog Post 4).",
            )
            return fn["FunctionArn"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidParameterValueException" and attempt < 9:
                log("  ...waiting for the IAM role to propagate.")
                time.sleep(5)
                continue
            raise
    raise RuntimeError("Lambda creation kept failing on role propagation.")


def main() -> int:
    session = boto3.Session(region_name=REGION)
    ddb = session.resource("dynamodb")
    iam = session.client("iam")
    lam = session.client("lambda")

    table_arn = ensure_table(ddb)
    role_arn = ensure_role(iam, table_arn)
    function_arn = ensure_function(lam, role_arn)

    log("Done.")
    # The ARN goes to stdout (capture this); progress goes to stderr.
    print(f"NOTES_AGENT_BACKEND_LAMBDA_ARN={function_arn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
