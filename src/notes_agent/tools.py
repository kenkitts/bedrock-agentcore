"""In-memory note tools for the Post 1 (local) agent.

These are intentionally trivial and stateful only for the life of the process.
Later posts replace this store with a real notes/bookmarks API behind an
AgentCore Gateway (Post 4) and per-user scoping via Identity (Post 5).

The functions are plain and deterministic on purpose: from Post 4 onward they
are unit-tested directly (see ``tests/``), independent of the LLM.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from strands import tool


@dataclass
class _NoteStore:
    """Process-local note store. Replaced by a real API in Post 4."""

    notes: list[dict] = field(default_factory=list)

    def add(self, text: str) -> dict:
        note = {
            "id": len(self.notes) + 1,
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.notes.append(note)
        return note

    def all(self) -> list[dict]:
        return list(self.notes)

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        return [n for n in self.notes if q in n["text"].lower()]


# Single shared store for the local REPL session.
_STORE = _NoteStore()


@tool
def add_note(text: str) -> str:
    """Save a note.

    Args:
        text: The note content to store.
    """
    note = _STORE.add(text)
    return f"Saved note #{note['id']}."


@tool
def list_notes() -> str:
    """List all saved notes."""
    notes = _STORE.all()
    if not notes:
        return "No notes yet."
    return "\n".join(f"#{n['id']}: {n['text']}" for n in notes)


@tool
def search_notes(query: str) -> str:
    """Search saved notes for a substring.

    Args:
        query: Text to search for within notes.
    """
    matches = _STORE.search(query)
    if not matches:
        return f"No notes matching {query!r}."
    return "\n".join(f"#{n['id']}: {n['text']}" for n in matches)


NOTE_TOOLS = [add_note, list_notes, search_notes]
