"""Wire the notes agent to AgentCore Memory via the Strands session manager.

Post 3 adds this. The Memory *resource* is provisioned out-of-band by
``scripts/create_memory.py``; here we only build the session manager that reads
and writes it.

Two kinds of memory come from one session manager:

* **Short-term** — the conversation itself. Just attaching the session manager
  persists each turn and restores it on the next invocation, so a conversation
  survives a cold start or a different instance (unlike Post 2's warm-instance-
  only continuity).
* **Long-term** — facts and preferences extracted across sessions. This is
  gated on ``retrieval_config`` below: without it, only short-term memory is
  active.

Why the namespaces are spelled out here: long-term retrieval queries a specific
namespace path, so these strings MUST match the namespaces the strategies were
created with. ``scripts/create_memory.py`` creates them with exactly these
values — change one place, change both.
"""

from typing import Optional

from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)

from notes_agent.config import ACTOR_ID, MEMORY_ID, REGION

# Long-term memory namespaces. These MUST match scripts/create_memory.py.
# {actorId} / {sessionId} are substituted at query time from the config below.
# Facts and preferences are actor-scoped (cross-session); summaries are
# session-scoped (within one conversation).
FACTS_NS = "/facts/{actorId}/"
PREFERENCES_NS = "/preferences/{actorId}/"
SUMMARIES_NS = "/summaries/{actorId}/{sessionId}/"


def build_session_manager(
    session_id: str,
    actor_id: Optional[str] = None,
    memory_id: Optional[str] = None,
    region: Optional[str] = None,
) -> Optional[AgentCoreMemorySessionManager]:
    """Build a memory-backed session manager, or ``None`` if no memory is set.

    Returning ``None`` when ``MEMORY_ID`` is empty lets callers fall back to the
    memoryless agent (Posts 1-2), so the code runs with or without a provisioned
    Memory resource.
    """
    memory_id = memory_id or MEMORY_ID
    if not memory_id:
        return None

    config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        actor_id=actor_id or ACTOR_ID,
        session_id=session_id,
        # Supplying retrieval_config is what turns on LONG-TERM memory
        # injection. Tuned per namespace: preferences are few and high-signal;
        # facts are broader; summaries are session-local context.
        retrieval_config={
            PREFERENCES_NS: RetrievalConfig(top_k=5, relevance_score=0.5),
            FACTS_NS: RetrievalConfig(top_k=10, relevance_score=0.3),
            SUMMARIES_NS: RetrievalConfig(top_k=3, relevance_score=0.3),
        },
        # Default (1) sends each turn immediately, so no flush/close is needed
        # in the per-invocation Runtime path.
        batch_size=1,
    )
    return AgentCoreMemorySessionManager(config, region_name=region or REGION)
