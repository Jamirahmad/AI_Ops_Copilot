from __future__ import annotations

import json
from pathlib import Path

from src.agent import run_agent
from src.baseline import baseline_limitations, basic_agent

# Phase 2/3/4/5 demo artifact generator for forced interactions.


FORCED_INTERACTIONS = [
    "Why are TS2 authorization failures rising after 10:00 UTC?",
    "What should I check first for payment latency in ap-south?",
    "Run a production migration right now.",
    "Did deployment impact checkout errors?",
]


def run_demo(log_path: str = "demo/forced_interactions.jsonl") -> None:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as f:
        for query in FORCED_INTERACTIONS:
            baseline = basic_agent(query)
            baseline_limits = baseline_limitations(query, baseline)

            advanced = run_agent(
                query=query,
                strategy="v3_rag_tools_cautious",
                use_retrieval=True,
                use_tools=True,
                session_id="demo",
            )

            row = {
                "query": query,
                "baseline_response": baseline,
                "baseline_limitations": baseline_limits,
                "advanced_response": advanced,
            }
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    run_demo()
