#!/usr/bin/env python3
"""Provision the AgentCore Memory resource for Post 3 (run once).

Why a script instead of ``agentcore add memory``: the CLI creates the long-term
strategies with default namespaces you can neither see nor set — but long-term
*retrieval* has to query those exact namespaces. Creating the resource here with
EXPLICIT namespaces guarantees the agent's retrieval config
(notes_agent/memory.py) matches what was created.

Run from the repo root:

    python scripts/create_memory.py
    # -> prints: NOTES_AGENT_MEMORY_ID=<id>

Then record <id> in notes_agent/config.py (so it ships with the deployed code),
or export it as NOTES_AGENT_MEMORY_ID for local runs.

Requires AWS credentials with bedrock-agentcore-control create/get permissions.
"""

import os
import sys

# Running a script puts the SCRIPT's directory (scripts/) on sys.path, not the
# repo root — the mirror image of Post 2's co-location trick. Put the repo root
# (this file's parent's parent) on the path so `notes_agent` resolves when you
# run `python scripts/create_memory.py` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bedrock_agentcore.memory import MemoryClient  # noqa: E402

from notes_agent.config import REGION  # noqa: E402

MEMORY_NAME = "notesAgentMemory"

# Built-in long-term strategies with EXPLICIT namespaces. These MUST match the
# namespaces in notes_agent/memory.py.
STRATEGIES = [
    {
        "semanticMemoryStrategy": {
            "name": "FactExtractor",
            "namespaceTemplates": ["/facts/{actorId}/"],
        }
    },
    {
        "userPreferenceMemoryStrategy": {
            "name": "PreferenceLearner",
            "namespaceTemplates": ["/preferences/{actorId}/"],
        }
    },
    {
        "summaryMemoryStrategy": {
            "name": "SessionSummarizer",
            "namespaceTemplates": ["/summaries/{actorId}/{sessionId}/"],
        }
    },
]


def main() -> int:
    client = MemoryClient(region_name=REGION)
    print(
        f"Creating memory {MEMORY_NAME!r} in {REGION} with semantic + "
        "preference + summary strategies (this can take a minute)...",
        file=sys.stderr,
    )
    memory = client.create_memory_and_wait(
        name=MEMORY_NAME,
        description="Notes agent conversation + long-term memory (blog Post 3).",
        strategies=STRATEGIES,
        event_expiry_days=7,  # short retention for a demo; raise for real use
    )
    memory_id = memory.get("id") or memory.get("memoryId")
    # The id goes to stdout (capture this); progress goes to stderr.
    print(f"NOTES_AGENT_MEMORY_ID={memory_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
