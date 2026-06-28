"""Central configuration for the notes agent.

A reader can swap the model or region in exactly one place — here.

NOTE: Bedrock model IDs change over time and model access must be explicitly
enabled per account/region in the Bedrock console. Before running Post 1,
confirm this model ID is current and that you have access in ``REGION``.
"""

import os

# Region used throughout the series. us-east-1 has the broadest AgentCore +
# Bedrock model availability.
REGION = os.environ.get("AWS_REGION", "us-east-1")

# Claude (Sonnet-class) is the default for its reliable tool-calling, which is
# the backbone of an agent. This is a cross-region inference profile (the "us."
# prefix), which the newer Sonnet models require. Amazon Nova
# (e.g. "amazon.nova-pro-v1:0") is a cheaper, AWS-native alternative if you want
# to trade some tool-calling robustness for cost.
MODEL_ID = os.environ.get(
    "MODEL_ID",
    "us.anthropic.claude-sonnet-4-6",
)


# --- Post 3 (Memory) -------------------------------------------------------

# AgentCore Memory resource id. Create the resource ONCE with
#   python scripts/create_memory.py
# and paste the printed id here as the default (it then ships with the bundled
# code into the Runtime container, since the AgentCore CLI has no way to inject
# env vars). For local runs you can instead export NOTES_AGENT_MEMORY_ID.
# Leave empty to run the memoryless Post 1/2 agent.
MEMORY_ID = os.environ.get("NOTES_AGENT_MEMORY_ID", "")

# Who the long-term memories belong to. Real per-user identity arrives in
# Post 5 (Identity); until then a single demo actor scopes all memory.
ACTOR_ID = os.environ.get("NOTES_AGENT_ACTOR_ID", "demo-user")
