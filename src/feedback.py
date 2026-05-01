from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict

from src.config import FEEDBACK_PATH

# Phase 7: Feedback capture and adaptive behavior signal computation.


def _append_feedback(record: Dict[str, object]) -> None:
    Path(FEEDBACK_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")


def store_feedback(query: str, rating: int, notes: str = "", session_id: str = "default") -> Dict[str, object]:
    rating = max(1, min(5, int(rating)))
    record = {
        "ts": time.time(),
        "session_id": session_id,
        "query": query,
        "rating": rating,
        "notes": notes,
    }
    _append_feedback(record)
    return record


def _load_feedback() -> list:
    path = Path(FEEDBACK_PATH)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def adaptive_instruction() -> str:
    rows = _load_feedback()
    if not rows:
        return ""

    recent = rows[-20:]
    avg = sum(r.get("rating", 3) for r in recent) / len(recent)

    if avg < 3.0:
        return "Use clearer structure, include concrete next actions, and state uncertainty early."
    if avg < 4.0:
        return "Keep responses concise but include explicit evidence and confidence."
    return ""
