from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

# Phase 2: Basic working baseline agent with rules/templates + logged samples.

BASELINE_TEMPLATES = {
    "failure": "Check system logs for failure spikes and retry error trends.",
    "deployment": "Review recent deployment history and compare before/after metrics.",
    "latency": "Inspect service latency dashboards and downstream dependency health.",
    "auth": "Verify auth service status, token expiry rates, and permission changes.",
}


def basic_agent(query: str) -> str:
    lowered = query.lower()
    for keyword, template in BASELINE_TEMPLATES.items():
        if keyword in lowered:
            return template
    return "Insufficient information. Please provide more details."


def baseline_limitations(query: str, response: str) -> List[str]:
    limits = []
    if "Insufficient information" in response:
        limits.append("Cannot infer intent for queries outside hardcoded keywords.")
    if "because" not in response.lower() and "evidence" not in response.lower():
        limits.append("No evidence grounding; response is generic and non-specific.")
    if len(response.split()) < 12:
        limits.append("Low actionability; lacks prioritized step-by-step guidance.")
    return limits[:3]


def run_baseline_samples(samples: List[str], log_path: str = "demo/baseline_samples.jsonl") -> List[Dict[str, object]]:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for q in samples:
        start = time.time()
        r = basic_agent(q)
        limitations = baseline_limitations(q, r)
        row = {
            "query": q,
            "response": r,
            "latency_sec": round(time.time() - start, 4),
            "limitations": limitations,
        }
        rows.append(row)

    with open(log_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    return rows
