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
