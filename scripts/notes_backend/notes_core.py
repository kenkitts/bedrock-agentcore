"""Pure notes logic for the Post 4 Gateway backend Lambda.

This module deliberately imports nothing from AWS. Everything here is plain,
deterministic Python so it can be unit-tested without a network, an account, or
a mock (see tests/test_notes_backend.py). That separation is the point of the
"B-lite testing starts here" beat: the tool logic is testable in isolation, and
the LLM is nowhere near these assertions.

``handler.py`` is the thin AWS adapter: it builds a DynamoDB-backed store and
hands it to :func:`handle_tool`, which contains all the actual behavior.
"""

from datetime import datetime, timezone
from typing import Optional, Protocol
import uuid

# AgentCore Gateway exposes a tool as ``${target_name}___${tool_name}`` (three
# underscores). The Lambda receives the *prefixed* name, so we strip the target
# prefix back off before dispatching. See "Understand how AgentCore Gateway
# tools are named" in the AgentCore docs.
DELIMITER = "___"


class NoteStore(Protocol):
    """The storage surface :func:`handle_tool` needs.

    DynamoDB implements this in ``handler.py``; the tests implement it with a
    plain list. ``handle_tool`` doesn't know or care which.
    """

    def add(self, note: dict) -> None: ...
    def all(self) -> list[dict]: ...


def strip_tool_prefix(raw_name: str) -> str:
    """Turn ``NotesTarget___add_note`` into ``add_note``.

    Robust to a missing prefix (returns the name unchanged) so a direct invoke
    during testing doesn't have to fake the gateway's naming convention.
    """
    return raw_name.split(DELIMITER, 1)[-1]


def build_note(text: str, *, now: Optional[str] = None, note_id: Optional[str] = None) -> dict:
    """Shape a note record. Pure: caller injects ``now``/``note_id`` for tests."""
    return {
        "id": note_id or uuid.uuid4().hex,
        "text": text,
        "created_at": now or datetime.now(timezone.utc).isoformat(),
    }


def search_notes(notes: list[dict], query: str) -> list[dict]:
    """Case-insensitive substring match over note text."""
    q = query.lower()
    return [n for n in notes if q in n.get("text", "").lower()]


def _sorted(notes: list[dict]) -> list[dict]:
    return sorted(notes, key=lambda n: n.get("created_at", ""))


def render_saved(note: dict) -> str:
    return f"Saved note: {note['text']!r}"


def render_list(notes: list[dict]) -> str:
    if not notes:
        return "No notes yet."
    return "\n".join(f"{i}. {n['text']}" for i, n in enumerate(_sorted(notes), start=1))


def render_search(matches: list[dict], query: str) -> str:
    if not matches:
        return f"No notes matching {query!r}."
    return "\n".join(f"- {n['text']}" for n in _sorted(matches))


def handle_tool(tool_name: str, args: Optional[dict], store: NoteStore) -> str:
    """Dispatch a single tool call against ``store`` and return the result text.

    ``args`` is the Gateway ``event`` object: a flat map of the tool's
    ``inputSchema`` properties to their values (e.g. ``{"text": "..."}``).
    Returns a plain string, which the gateway delivers to the agent as the
    tool result.
    """
    args = args or {}

    if tool_name == "add_note":
        text = str(args.get("text", "")).strip()
        if not text:
            return "Cannot save an empty note."
        note = build_note(text)
        store.add(note)
        return render_saved(note)

    if tool_name == "list_notes":
        return render_list(store.all())

    if tool_name == "search_notes":
        query = str(args.get("query", ""))
        return render_search(search_notes(store.all(), query), query)

    raise ValueError(f"Unknown tool: {tool_name!r}")
