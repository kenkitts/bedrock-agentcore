#!/usr/bin/env python3
"""Mint a Cognito access token for a demo user (Post 5).

Uses AdminInitiateAuth (USER_PASSWORD_AUTH flow) to get tokens without a
browser or callback server. Run this whenever you need a fresh token for the
demo — tokens expire after 1 hour.

Usage:

    python scripts/get_token.py alice
    python scripts/get_token.py bob

    # Output:
    #   export NOTES_AGENT_TOKEN=eyJ...

    # Then invoke the agent:
    agentcore invoke --bearer-token "$NOTES_AGENT_TOKEN" "add a note: meeting at 3pm"

Prerequisites:

    python scripts/create_cognito.py   # creates the pool + users (once)

    # Export these (printed by create_cognito.py):
    export NOTES_AGENT_COGNITO_POOL_ID=us-east-1_XXXXXXXXX
    export NOTES_AGENT_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx

The demo user passwords are hardcoded here (matching create_cognito.py). In
production you'd never do this — the point is to make the demo zero-friction.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3  # noqa: E402

from notes_agent.config import REGION  # noqa: E402

# Demo credentials — must match create_cognito.py.
DEMO_USERS = {
    "alice": "Alice123!demo",
    "bob": "Bob456!demo",
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in DEMO_USERS:
        users = ", ".join(DEMO_USERS.keys())
        print(f"Usage: python scripts/get_token.py <{users}>", file=sys.stderr)
        return 1

    username = sys.argv[1]
    password = DEMO_USERS[username]

    pool_id = os.environ.get("NOTES_AGENT_COGNITO_POOL_ID", "")
    client_id = os.environ.get("NOTES_AGENT_COGNITO_CLIENT_ID", "")

    if not pool_id or not client_id:
        print(
            "ERROR: NOTES_AGENT_COGNITO_POOL_ID and NOTES_AGENT_COGNITO_CLIENT_ID must be set.\n"
            "Run: python scripts/create_cognito.py  (and export the printed values)",
            file=sys.stderr,
        )
        return 1

    client = boto3.client("cognito-idp", region_name=REGION)

    print(f"Authenticating as {username!r}...", file=sys.stderr)
    resp = client.admin_initiate_auth(
        UserPoolId=pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
        },
    )

    result = resp.get("AuthenticationResult", {})
    access_token = result.get("AccessToken")
    if not access_token:
        # Might get a challenge (shouldn't with permanent password, but just in case).
        challenge = resp.get("ChallengeName", "unknown")
        print(f"ERROR: Got challenge {challenge!r} instead of tokens.", file=sys.stderr)
        print("Ensure the user's password is set as permanent.", file=sys.stderr)
        return 1

    # Print as shell export — use `eval $(python scripts/get_token.py alice)`.
    print(f"export NOTES_AGENT_TOKEN={access_token}")

    id_token = result.get("IdToken", "")
    print(f"\n# Authenticated as: {username}", file=sys.stderr)
    print(f"# Access token expires in: {result.get('ExpiresIn', '?')}s", file=sys.stderr)
    print(f"#", file=sys.stderr)
    print(f"# Use with:", file=sys.stderr)
    print(f"#   agentcore invoke --bearer-token \"$NOTES_AGENT_TOKEN\" \"list my notes\"", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
