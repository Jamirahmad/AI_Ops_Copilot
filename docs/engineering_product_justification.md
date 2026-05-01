# Engineering & Product Justification

## Why This Architecture

- FastAPI backend enables clear API surface for query, streaming, evaluation, memory, and feedback.
- Plain HTML/CSS/JS frontend keeps deployment simple while preserving interactive capability.
- Retrieval + tools + safety/quality gates are required for practical AI Ops use under incident pressure.

## Product Decisions

- Response schema is enforced for readability and consistency.
- Evidence-first behavior reduces hallucination risk.
- Feedback loop (thumbs) supports iterative behavior tuning.

## Data Strategy

- Canonical knowledge source is now PDF-based (`data/knowledge/*.pdf`).
- Synthetic high-volume operational datasets are used for stress/eval realism.
- Persisted KB artifacts (`chunks.jsonl`, `manifest`, `stats`, optional FAISS) improve reproducibility.

## Tradeoffs

- PDF-only ingestion simplifies source policy but requires good text extraction quality.
- Large datasets improve realism but increase build and storage cost.
- Hybrid retrieval improves robustness but adds pipeline complexity.

## Readiness Summary

The current system is suitable for evaluator review as a phase-wise AI Ops copilot prototype with realistic data scale, clear safety controls, and auditable outputs.
