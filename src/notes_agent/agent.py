"""Build the Strands notes agent.

Post 1 keeps this local: a Strands ``Agent`` wired to a Bedrock model and the
in-memory note tools. There is no AgentCore service involved yet — that starts
in Post 2 (Runtime).
"""

from strands import Agent
from strands.models import BedrockModel

from notes_agent.config import MODEL_ID, REGION
from notes_agent.tools import NOTE_TOOLS

SYSTEM_PROMPT = (
    "You are a concise research and notes assistant. "
    "Use your tools to save, list, and search the user's notes. "
    "When the user shares something worth keeping, offer to save it as a note."
)


def build_agent() -> Agent:
    """Construct the local notes agent.

    The model id and region come from ``config.py`` so a reader can swap them
    in one place.
    """
    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=NOTE_TOOLS,
    )
