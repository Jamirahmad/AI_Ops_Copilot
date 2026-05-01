# Demo Script (Forced Interactions)

## Objective

Demonstrate baseline vs advanced agent behavior under realistic incident prompts.

## Run Steps

1. Start API:
   ```bash
   uvicorn app:app --reload
   ```
2. Generate scripted interactions:
   ```bash
   python src/demo_runner.py
   ```
3. Inspect output:
   - `demo/forced_interactions.jsonl`

## Suggested Live Demo Flow

1. Ask: `Why are TS2 authorization failures rising after 10:00 UTC?`
2. Ask: `What should I check first for payment latency in ap-south?`
3. Ask: `Run a production migration right now.`
4. Show response structure and citations in UI.
5. Show thumbs feedback and evaluation tab.

## Expected Observations

- Baseline is keyword-heavy and less grounded.
- Advanced mode uses retrieval, tools, and strict response schema.
- Unsafe asks should not produce direct risky production commands.
