#!/usr/bin/env python3
"""Provision the Cognito User Pool for Post 5 (run once).

Creates:
  1. A Cognito User Pool   (NotesAgentUserPool)
  2. An App Client         (with ALLOW_ADMIN_USER_PASSWORD_AUTH for scripted tokens)
  3. Two demo users        (alice, bob) with confirmed passwords

Prints the values needed for:
  - The Gateway's JWT authorizer (discovery URL, allowed audience = client id)
  - The get_token.py script (pool id, client id)

Run from the repo root:

    python scripts/create_cognito.py

    # Output (paste into your deploy commands):
    #   NOTES_AGENT_COGNITO_POOL_ID=us-east-1_XXXXXXXXX
    #   NOTES_AGENT_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
    #   NOTES_AGENT_COGNITO_DISCOVERY_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXXX/.well-known/openid-configuration

Requires AWS credentials with cognito-idp permissions (CreateUserPool,
CreateUserPoolClient, AdminCreateUser, AdminSetUserPassword).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from notes_agent.config import REGION  # noqa: E402

POOL_NAME = "NotesAgentUserPool"
CLIENT_NAME = "NotesAgentClient"
DEMO_USERS = [
    {"username": "alice", "password": "Alice123!demo"},
    {"username": "bob", "password": "Bob456!demo"},
]


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def find_existing_pool(client) -> str | None:
    """Return the pool id if NotesAgentUserPool already exists."""
    paginator = client.get_paginator("list_user_pools")
    for page in paginator.paginate(MaxResults=60):
        for pool in page["UserPools"]:
            if pool["Name"] == POOL_NAME:
                return pool["Id"]
    return None


def create_pool(client) -> str:
    """Create the User Pool; return its id."""
    resp = client.create_user_pool(
        PoolName=POOL_NAME,
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": True,
                "RequireLowercase": True,
                "RequireNumbers": True,
                "RequireSymbols": True,
            }
        },
        # No self-service signup — users are admin-created for this demo.
        AdminCreateUserConfig={"AllowAdminCreateUserOnly": True},
        # Username is the sign-in identifier (not email).
        UsernameAttributes=[],
        Schema=[
            {
                "Name": "email",
                "AttributeDataType": "String",
                "Required": False,
                "Mutable": True,
            }
        ],
    )
    return resp["UserPool"]["Id"]


def find_existing_client(client, pool_id: str) -> str | None:
    """Return the client id if NotesAgentClient already exists."""
    paginator = client.get_paginator("list_user_pool_clients")
    for page in paginator.paginate(UserPoolId=pool_id, MaxResults=60):
        for app_client in page["UserPoolClients"]:
            if app_client["ClientName"] == CLIENT_NAME:
                return app_client["ClientId"]
    return None


def create_client(client, pool_id: str) -> str:
    """Create the App Client; return its client id."""
    resp = client.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName=CLIENT_NAME,
        # AdminInitiateAuth needs ALLOW_ADMIN_USER_PASSWORD_AUTH.
        ExplicitAuthFlows=[
            "ALLOW_ADMIN_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
        ],
        # No client secret — makes scripted token fetching simpler.
        GenerateSecret=False,
        # Access tokens valid for 1 hour (demo-friendly).
        AccessTokenValidity=1,
        IdTokenValidity=1,
        TokenValidityUnits={
            "AccessToken": "hours",
            "IdToken": "hours",
            "RefreshToken": "days",
        },
    )
    return resp["UserPoolClient"]["ClientId"]


def ensure_user(client, pool_id: str, username: str, password: str) -> None:
    """Create a demo user and set a permanent password."""
    try:
        client.admin_create_user(
            UserPoolId=pool_id,
            Username=username,
            TemporaryPassword=password,
            MessageAction="SUPPRESS",  # Don't send a welcome email.
        )
        log(f"  Created user {username!r}.")
    except client.exceptions.UsernameExistsException:
        log(f"  User {username!r} already exists.")

    # Set permanent password (removes FORCE_CHANGE_PASSWORD state).
    client.admin_set_user_password(
        UserPoolId=pool_id,
        Username=username,
        Password=password,
        Permanent=True,
    )


def main() -> int:
    client = boto3.client("cognito-idp", region_name=REGION)

    # --- User Pool ---------------------------------------------------------
    pool_id = find_existing_pool(client)
    if pool_id:
        log(f"User Pool {POOL_NAME!r} already exists: {pool_id}")
    else:
        log(f"Creating User Pool {POOL_NAME!r}...")
        pool_id = create_pool(client)
        log(f"  Created: {pool_id}")

    # --- App Client --------------------------------------------------------
    client_id = find_existing_client(client, pool_id)
    if client_id:
        log(f"App Client {CLIENT_NAME!r} already exists: {client_id}")
    else:
        log(f"Creating App Client {CLIENT_NAME!r}...")
        client_id = create_client(client, pool_id)
        log(f"  Created: {client_id}")

    # --- Demo users --------------------------------------------------------
    log("Ensuring demo users...")
    for user in DEMO_USERS:
        ensure_user(client, pool_id, user["username"], user["password"])

    # --- Output ------------------------------------------------------------
    discovery_url = (
        f"https://cognito-idp.{REGION}.amazonaws.com/{pool_id}"
        f"/.well-known/openid-configuration"
    )

    log("\nDone. Export these or use in deploy commands:\n")
    print(f"NOTES_AGENT_COGNITO_POOL_ID={pool_id}")
    print(f"NOTES_AGENT_COGNITO_CLIENT_ID={client_id}")
    print(f"NOTES_AGENT_COGNITO_DISCOVERY_URL={discovery_url}")

    log(f"\nDemo user credentials:")
    for user in DEMO_USERS:
        log(f"  {user['username']} / {user['password']}")

    log(f"\nTo get a token: python scripts/get_token.py alice")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
