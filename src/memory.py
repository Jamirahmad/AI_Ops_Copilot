from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from src.config import MAX_MEMORY_TURNS, MEMORY_PATH

# Phase 6: Short-term/long-term conversation memory persistence and reset.


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _load_store() -> Dict[str, List[dict]]:
    path = Path(MEMORY_PATH)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_store(store: Dict[str, List[dict]]) -> None:
    _ensure_parent(MEMORY_PATH)
    Path(MEMORY_PATH).write_text(json.dumps(store, indent=2), encoding="utf-8")


def append_turn(session_id: str, user_query: str, agent_response: str) -> None:
    store = _load_store()
    session = store.get(session_id, [])
    session.append({"user": user_query, "assistant": agent_response})
    session = session[-MAX_MEMORY_TURNS:]
    store[session_id] = session
    _save_store(store)


def get_recent_turns(session_id: str) -> List[dict]:
    store = _load_store()
    return store.get(session_id, [])[-MAX_MEMORY_TURNS:]


def reset_memory(session_id: str | None = None) -> None:
    store = _load_store()
    if session_id is None:
        store = {}
    else:
        store.pop(session_id, None)
    _save_store(store)


def memory_summary(session_id: str) -> str:
    turns = get_recent_turns(session_id)
    if not turns:
        return "No prior context."

    lines = []
    for t in turns:
        lines.append(f"User: {t['user']}")
        lines.append(f"Assistant: {t['assistant']}")
    return "\n".join(lines)
