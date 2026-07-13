#!/usr/bin/env python3
"""Deploy the Gateway REQUEST interceptor Lambda (Post 5, run once).

The interceptor sits between the Gateway and the notes backend Lambda. After
the Gateway validates the user's JWT, it invokes this interceptor which:

  1. Reads the validated JWT from the Authorization header.
  2. Decodes it (no signature verification needed — the Gateway already did
     that) to extract the ``sub`` claim.
  3. Injects ``{"__authContext": {"userAlias": sub}}`` into the tool arguments
     so the notes backend Lambda receives the authenticated user's identity on
     a trusted channel the model never touches.

This is the documented pattern for passing user identity to Gateway Lambda
targets. The interceptor is ~15 lines of actual logic.

Run from the repo root:

    python scripts/create_interceptor.py

Prints the Lambda ARN, which you register as the Gateway's request interceptor
via the AgentCore CLI.

Requires AWS credentials with Lambda + IAM permissions.
"""

import io
import json
import os
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from notes_agent.config import REGION  # noqa: E402

ROLE_NAME = "NotesAgentInterceptorRole"
FUNCTION_NAME = "NotesAgentInterceptor"
RUNTIME = "python3.12"
HANDLER = "interceptor.lambda_handler"

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

# The interceptor Lambda source code — small enough to inline here.
INTERCEPTOR_CODE = '''\
"""AgentCore Gateway REQUEST interceptor for identity injection (Post 5).

The Gateway validates the JWT before invoking this function. We decode the
already-validated token to extract the ``sub`` claim and inject it into the
tool arguments so the notes backend Lambda receives trusted user identity.
"""

import base64
import json


def _decode_jwt_payload(token: str) -> dict:
    """Decode the payload segment of a JWT without verification.

    We skip signature verification because the Gateway already validated the
    token. This avoids needing PyJWT or cryptographic libraries in the
    interceptor Lambda (keeps the deployment package tiny).
    """
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    # JWT base64url decoding: restore padding.
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    try:
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


def lambda_handler(event, context):
    """Extract user identity from JWT and inject into tool arguments."""
    gateway_request = event.get("mcp", {}).get("gatewayRequest", {})
    headers = gateway_request.get("headers", {})
    body = gateway_request.get("body", {})

    # Extract sub from the Authorization header (Bearer <JWT>).
    auth_header = headers.get("Authorization", "") or headers.get("authorization", "")
    user_alias = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        claims = _decode_jwt_payload(token)
        user_alias = claims.get("sub", "")

    # Inject identity into tool arguments on a trusted key.
    if user_alias:
        params = body.setdefault("params", {})
        arguments = params.setdefault("arguments", {})
        arguments["__authContext"] = {"userAlias": user_alias}

    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "headers": headers,
                "body": body,
            }
        }
    }
'''


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def ensure_role(iam) -> str:
    """Create the interceptor Lambda execution role if absent."""
    try:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(LAMBDA_TRUST),
            Description="Execution role for the notes agent Gateway interceptor Lambda (Post 5).",
        )
        role_arn = role["Role"]["Arn"]
        log(f"Created role {ROLE_NAME!r}.")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        log(f"Role {ROLE_NAME!r} already exists.")

    # Only needs basic logging — the interceptor calls no other AWS services.
    iam.attach_role_policy(
        RoleName=ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    return role_arn


def _zip_interceptor() -> bytes:
    """Package the interceptor code into a deployment zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("interceptor.py", INTERCEPTOR_CODE)
    return buf.getvalue()


def ensure_function(lam, role_arn: str) -> str:
    """Create or update the interceptor Lambda; return its ARN."""
    code = _zip_interceptor()

    try:
        fn = lam.get_function(FunctionName=FUNCTION_NAME)
        log(f"Function {FUNCTION_NAME!r} exists; updating code.")
        lam.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=code)
        return fn["Configuration"]["FunctionArn"]
    except lam.exceptions.ResourceNotFoundException:
        pass

    log(f"Creating Lambda {FUNCTION_NAME!r}...")
    for attempt in range(10):
        try:
            fn = lam.create_function(
                FunctionName=FUNCTION_NAME,
                Runtime=RUNTIME,
                Role=role_arn,
                Handler=HANDLER,
                Code={"ZipFile": code},
                Timeout=10,
                Description="Gateway request interceptor for identity injection (blog Post 5).",
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
    iam = session.client("iam")
    lam = session.client("lambda")

    role_arn = ensure_role(iam)
    function_arn = ensure_function(lam, role_arn)

    log("Done.")
    print(f"NOTES_AGENT_INTERCEPTOR_LAMBDA_ARN={function_arn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
