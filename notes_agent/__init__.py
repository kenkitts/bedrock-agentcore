"""A research / notes assistant built with Strands Agents.

This package grows across the blog series. At Post 1 it is a purely local
agent with in-memory note tools and no AgentCore services.
"""

__all__ = ["build_agent", "NOTE_TOOLS"]

from notes_agent.agent import build_agent
from notes_agent.tools import NOTE_TOOLS
