"""AgentCore Gateway target Lambda for the notes agent (Post 4, updated Post 5).

This is the "real" notes backend that replaces the in-memory Python list from
Posts 1-3. The Gateway invokes this function once per tool call; the function
reads/writes a DynamoDB table so notes finally survive a restart.

All behavior lives in ``notes_core`` (pure, unit-tested). This file is just the
AWS adapter:

* It reads the called tool name from the *context* object (the Gateway passes
  it as ``bedrockAgentCoreToolName`` in the ``${target}___${tool}`` form).
* It extracts the authenticated user's identity from the interceptor-injected
  field in the event (Post 5).
* It wraps a DynamoDB table in the tiny ``NoteStore`` surface ``notes_core``
  expects — now with a composite key (``user_id`` PK + ``note_id`` SK) for
  per-user isolation.

The Gateway delivers our string return value to the agent as the tool result.
"""

import os

import boto3
from boto3.dynamodb.conditions import Key

from notes_core import handle_tool, strip_tool_prefix

TABLE_NAME = os.environ.get("NOTES_TABLE", "NotesAgentNotes")

# The key in the event where the interceptor Lambda injects the authenticated
# user's identity. The interceptor decodes the Gateway-validated JWT and places
# the ``sub`` claim here before forwarding to this Lambda.
AUTH_CONTEXT_KEY = "__authContext"
USER_ALIAS_KEY = "userAlias"


def _extract_user_id(event: dict) -> str:
    """Extract the user identity injected by the Gateway interceptor.

    The interceptor Lambda reads the validated JWT's ``sub`` claim and places
    it in ``event["__authContext"]["userAlias"]``. This is a trusted channel —
    the model never touches it.

    Falls back to "anonymous" if missing (shouldn't happen with a correctly
    configured interceptor, but avoids crashing during development).
    """
    auth_context = event.pop(AUTH_CONTEXT_KEY, None)
    if auth_context and isinstance(auth_context, dict):
        user = auth_context.get(USER_ALIAS_KEY, "")
        if user:
            return user
    return "anonymous"


class DynamoNoteStore:
    """A ``notes_core.NoteStore`` backed by a DynamoDB table.

    Post 5: the table uses a composite key (``user_id`` partition key,
    ``note_id`` sort key). Each user's notes live in their own partition, so
    queries are naturally scoped — no scan + filter.
    """

    def __init__(self, table):
        self._table = table

    def add(self, note: dict, user_id: str) -> None:
        item = {**note, "user_id": user_id, "note_id": note["id"]}
        self._table.put_item(Item=item)

    def all(self, user_id: str) -> list[dict]:
        resp = self._table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        # Return notes in the shape notes_core expects (id, text, created_at).
        return [
            {"id": item["note_id"], "text": item["text"], "created_at": item["created_at"]}
            for item in resp.get("Items", [])
        ]


def lambda_handler(event, context):
    # The visible tool name is prefixed with the target name; strip it back off.
    raw_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    tool_name = strip_tool_prefix(raw_tool_name)

    # Extract the user identity from the interceptor-injected field.
    # This mutates `event` (pops __authContext) so notes_core only sees tool args.
    user_id = _extract_user_id(event)

    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    store = DynamoNoteStore(table)

    # ``event`` is now the flat map of inputSchema properties -> values.
    return handle_tool(tool_name, event, store, user_id)
