"""AgentCore Gateway target Lambda for the notes agent (Post 4).

This is the "real" notes backend that replaces the in-memory Python list from
Posts 1-3. The Gateway invokes this function once per tool call; the function
reads/writes a DynamoDB table so notes finally survive a restart.

All behavior lives in ``notes_core`` (pure, unit-tested). This file is just the
AWS adapter:

* It reads the called tool name from the *context* object (the Gateway passes
  it as ``bedrockAgentCoreToolName`` in the ``${target}___${tool}`` form), and
* it wraps a DynamoDB table in the tiny ``NoteStore`` surface ``notes_core``
  expects.

The Gateway delivers our string return value to the agent as the tool result.
"""

import os

import boto3

from notes_core import handle_tool, strip_tool_prefix

TABLE_NAME = os.environ.get("NOTES_TABLE", "NotesAgentNotes")


class DynamoNoteStore:
    """A ``notes_core.NoteStore`` backed by a DynamoDB table.

    Search is done in memory after a scan: fine for a demo notes store, wrong
    for anything with real volume (you'd add a proper index or a search
    service). We call that out rather than pretend a scan scales.
    """

    def __init__(self, table):
        self._table = table

    def add(self, note: dict) -> None:
        self._table.put_item(Item=note)

    def all(self) -> list[dict]:
        return self._table.scan().get("Items", [])


def lambda_handler(event, context):
    # The visible tool name is prefixed with the target name; strip it back off.
    raw_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    tool_name = strip_tool_prefix(raw_tool_name)

    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    store = DynamoNoteStore(table)

    # ``event`` is the flat map of inputSchema properties -> values.
    return handle_tool(tool_name, event, store)
