"""Unit tests for the notes backend's pure core (Post 4).

This is where the series' B-lite testing starts: deterministic tool logic,
tested with no AWS, no network, and no LLM. We import ``notes_core`` directly
(it imports nothing from boto3), drive it with a fake in-memory store, and
assert on the results.

The Lambda's DynamoDB adapter and the gateway wiring are exercised at deploy
time, not here - these tests cover the logic that's actually worth asserting.
"""

import os
import sys

import pytest

# notes_core lives beside the Lambda handler under scripts/notes_backend/, which
# isn't an installed package - put it on the path so we can import it directly.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "notes_backend"),
)

import notes_core  # noqa: E402


class FakeStore:
    """An in-memory NoteStore stand-in for the DynamoDB-backed one."""

    def __init__(self, notes=None):
        self.notes = list(notes or [])

    def add(self, note):
        self.notes.append(note)

    def all(self):
        return list(self.notes)


def _note(text, created_at, note_id="x"):
    return {"id": note_id, "text": text, "created_at": created_at}


# --- strip_tool_prefix -----------------------------------------------------

def test_strip_tool_prefix_removes_target_prefix():
    assert notes_core.strip_tool_prefix("NotesTarget___add_note") == "add_note"


def test_strip_tool_prefix_passes_through_unprefixed_name():
    # A direct invoke (no gateway prefix) should be left alone.
    assert notes_core.strip_tool_prefix("add_note") == "add_note"


def test_strip_tool_prefix_only_splits_first_delimiter():
    assert notes_core.strip_tool_prefix("T___odd___name") == "odd___name"


# --- build_note ------------------------------------------------------------

def test_build_note_shapes_record_and_injectable_fields():
    note = notes_core.build_note("buy milk", now="2026-01-01T00:00:00+00:00", note_id="abc")
    assert note == {"id": "abc", "text": "buy milk", "created_at": "2026-01-01T00:00:00+00:00"}


def test_build_note_generates_id_and_timestamp_when_omitted():
    note = notes_core.build_note("buy milk")
    assert note["text"] == "buy milk"
    assert note["id"]  # non-empty generated id
    assert note["created_at"]  # non-empty generated timestamp


# --- search_notes ----------------------------------------------------------

def test_search_notes_is_case_insensitive_substring():
    notes = [_note("Buy MILK", "1"), _note("call dentist", "2")]
    matches = notes_core.search_notes(notes, "milk")
    assert [n["text"] for n in matches] == ["Buy MILK"]


def test_search_notes_returns_empty_on_no_match():
    assert notes_core.search_notes([_note("a", "1")], "zzz") == []


# --- handle_tool dispatch --------------------------------------------------

def test_handle_tool_add_note_saves_and_confirms():
    store = FakeStore()
    out = notes_core.handle_tool("add_note", {"text": "the Q3 doc is in the drive"}, store)
    assert len(store.all()) == 1
    assert "the Q3 doc is in the drive" in out


def test_handle_tool_add_note_rejects_empty():
    store = FakeStore()
    out = notes_core.handle_tool("add_note", {"text": "   "}, store)
    assert store.all() == []
    assert "empty" in out.lower()


def test_handle_tool_list_notes_orders_by_created_at():
    store = FakeStore([_note("second", "2026-01-02"), _note("first", "2026-01-01")])
    out = notes_core.handle_tool("list_notes", {}, store)
    assert out == "1. first\n2. second"


def test_handle_tool_list_notes_empty():
    assert notes_core.handle_tool("list_notes", {}, FakeStore()) == "No notes yet."


def test_handle_tool_search_notes_filters():
    store = FakeStore([_note("buy milk", "1"), _note("call dentist", "2")])
    out = notes_core.handle_tool("search_notes", {"query": "milk"}, store)
    assert "buy milk" in out
    assert "dentist" not in out


def test_handle_tool_search_notes_no_match_message():
    store = FakeStore([_note("buy milk", "1")])
    out = notes_core.handle_tool("search_notes", {"query": "taxes"}, store)
    assert "taxes" in out
    assert "No notes matching" in out


def test_handle_tool_unknown_raises():
    with pytest.raises(ValueError):
        notes_core.handle_tool("delete_everything", {}, FakeStore())
