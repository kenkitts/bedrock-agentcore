"""Build the Strands notes agent.

Post 1 keeps this local: a Strands ``Agent`` wired to a Bedrock model and the
in-memory note tools. Post 2 (Runtime) hosts the same agent in the cloud.

Post 3 (Memory) adds one optional argument: a ``session_manager``. When given,
Strands persists the conversation to (and restores it from) AgentCore Memory,
and — with a retrieval config — injects long-term memories into the prompt.
When omitted, this is exactly the memoryless agent from Posts 1-2.
"""

from typing import Any, Optional

from strands import Agent
from strands.models import BedrockModel

from notes_agent.config import MODEL_ID, REGION
from notes_agent.tools import NOTE_TOOLS

SYSTEM_PROMPT = (
    "You are a concise research and notes assistant. "
    "Use your tools to save, list, and search the user's notes. "
    "When the user shares something worth keeping, offer to save it as a note. "
    "Use what you remember about the user — their stated preferences and the "
    "facts they've shared in earlier conversations — to tailor your answers."
)


def build_agent(
    session_manager: Optional[Any] = None,
    tools: Optional[list] = None,
) -> Agent:
    """Construct the notes agent.

    The model id and region come from ``config.py`` so a reader can swap them
    in one place.

    ``callback_handler=None`` disables Strands' built-in handler, which would
    otherwise stream the model's text to stdout as it generates. Our callers
    print the final result themselves, so without this we'd print twice.

    ``session_manager`` (Post 3) wires the agent to AgentCore Memory. It is
    optional: pass ``None`` (the default) for the memoryless Posts 1-2 agent.

    ``tools`` (Post 4) lets callers pass tools discovered over the AgentCore
    Gateway (MCP). When omitted, the agent uses the in-process ``NOTE_TOOLS``
    from Post 1, so it still runs with no gateway configured.
    """
    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    kwargs = {
        "model": model,
        "system_prompt": SYSTEM_PROMPT,
        "tools": tools if tools is not None else NOTE_TOOLS,
        "callback_handler": None,
    }
    if session_manager is not None:
        kwargs["session_manager"] = session_manager
    return Agent(**kwargs)
