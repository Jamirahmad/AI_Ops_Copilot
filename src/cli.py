from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agent import run_agent
from src.baseline import baseline_limitations, basic_agent

# Phase 2 helper: CLI flow for baseline/advanced interaction and sample logging.


def run_once(mode: str, query: str) -> dict:
    if mode == "baseline":
        response = basic_agent(query)
        limitations = baseline_limitations(query, response)
    else:
        response = run_agent(query)
        limitations = []

    return {
        "mode": mode,
        "query": query,
        "response": response,
        "limitations": limitations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Ops Copilot CLI")
    parser.add_argument("--mode", choices=["baseline", "advanced"], default="advanced")
    parser.add_argument("--query", required=False, help="Single query mode")
    parser.add_argument("--log", default="demo/sample_interactions.jsonl")
    args = parser.parse_args()

    Path(args.log).parent.mkdir(parents=True, exist_ok=True)

    if args.query:
        result = run_once(args.mode, args.query)
        print(result["response"])
        with open(args.log, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=True) + "\n")
        return

    print("AI Ops Copilot interactive mode. Type 'exit' to stop.")
    while True:
        query = input("You> ").strip()
        if query.lower() in {"exit", "quit"}:
            print("Session ended.")
            break

        result = run_once(args.mode, query)
        print(f"Copilot> {result['response']}")
        if result["limitations"]:
            print(f"Limitations> {', '.join(result['limitations'])}")

        with open(args.log, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
