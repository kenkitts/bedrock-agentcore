#!/usr/bin/env python3
"""Attach the request interceptor Lambda to the AgentCore Gateway (Post 5).

The AgentCore CLI doesn't expose interceptor configuration as a flag, so we
wire it post-deploy using the UpdateGateway API. Run this AFTER
`agentcore deploy -y` completes.

The interceptor extracts the authenticated user's ``sub`` claim from the
Gateway-validated JWT and injects it into tool arguments so the notes backend
Lambda receives trusted user identity.

Usage (from the repo root):

    python scripts/attach_interceptor.py <gateway-id> <interceptor-lambda-arn>

    # gateway-id: from `agentcore status --json` (the gateway identifier)
    # interceptor-lambda-arn: from `python scripts/create_interceptor.py`

Requires AWS credentials with bedrock-agentcore-control:UpdateGateway permission.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from notes_agent.config import REGION  # noqa: E402


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def attach_interceptor(gateway_id: str, interceptor_arn: str) -> None:
    """Attach a REQUEST interceptor to the gateway via UpdateGateway."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    # First, get the current gateway config so we can pass required fields.
    log(f"Reading gateway {gateway_id!r}...")
    gw = client.get_gateway(gatewayIdentifier=gateway_id)

    # UpdateGateway requires these fields even if unchanged.
    name = gw["name"]
    role_arn = gw["roleArn"]
    authorizer_type = gw["authorizerType"]

    # Build the interceptor configuration.
    interceptor_config = [
        {
            "interceptor": {"lambda": {"arn": interceptor_arn}},
            "interceptionPoints": ["REQUEST"],
            "inputConfiguration": {"passRequestHeaders": True},
        }
    ]

    log(f"Attaching interceptor {interceptor_arn!r}...")
    log(f"  interceptionPoints: REQUEST")
    log(f"  passRequestHeaders: true")

    # UpdateGateway with the interceptor configuration.
    update_kwargs = {
        "gatewayIdentifier": gateway_id,
        "name": name,
        "roleArn": role_arn,
        "authorizerType": authorizer_type,
        "interceptorConfigurations": interceptor_config,
    }

    # Preserve existing authorizer configuration if present.
    if "authorizerConfiguration" in gw:
        update_kwargs["authorizerConfiguration"] = gw["authorizerConfiguration"]

    # Preserve protocol configuration if present.
    if "protocolConfiguration" in gw:
        update_kwargs["protocolConfiguration"] = gw["protocolConfiguration"]

    client.update_gateway(**update_kwargs)

    log("Done. The interceptor is now active on the gateway.")
    log("Verify with: agentcore status --json")


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: python scripts/attach_interceptor.py <gateway-id> <interceptor-lambda-arn>\n"
            "\n"
            "  gateway-id:            from `agentcore status --json`\n"
            "  interceptor-lambda-arn: from `python scripts/create_interceptor.py`",
            file=sys.stderr,
        )
        return 1

    gateway_id = sys.argv[1].strip()
    interceptor_arn = sys.argv[2].strip()

    if not gateway_id or not interceptor_arn:
        print("ERROR: both gateway-id and interceptor-lambda-arn are required.", file=sys.stderr)
        return 1

    attach_interceptor(gateway_id, interceptor_arn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
