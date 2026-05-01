from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict

from src.config import ERROR_LOG_PATH, RUNTIME_LOG_PATH

# Phase 8: Deployment readiness logging/tracing (latency, errors, sanitization).


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def sanitize(text: str) -> str:
    if text is None:
        return ""
    masked = text
    masked = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_KEY]", masked)
    masked = re.sub(r"\b\d{12,19}\b", "[REDACTED_NUMBER]", masked)
    return masked


def _append_jsonl(path: str, payload: Dict[str, Any]) -> None:
    _ensure_parent(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def log_event(
    query: str,
    response: str,
    latency_sec: float,
    mode: str,
    prompt_strategy: str,
    retrieval_used: bool,
    tool_summary: str,
    confidence: str,
) -> None:
    payload = {
        "ts": time.time(),
        "query": sanitize(query),
        "response": sanitize(response),
        "latency_sec": round(latency_sec, 4),
        "mode": mode,
        "prompt_strategy": prompt_strategy,
        "retrieval_used": retrieval_used,
        "tool_summary": sanitize(tool_summary),
        "confidence": confidence,
    }
    _append_jsonl(RUNTIME_LOG_PATH, payload)


def log_error(context: str, error: Exception) -> None:
    payload = {
        "ts": time.time(),
        "context": sanitize(context),
        "error_type": type(error).__name__,
        "error": sanitize(str(error)),
    }
    _append_jsonl(ERROR_LOG_PATH, payload)
