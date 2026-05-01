# Engineering & Product Justification

## AI/LLM Design

The assistant is implemented as an LLM-orchestrated incident copilot using an OpenRouter-compatible API path.

- Model client: `ChatOpenAI` configured via OpenRouter settings in `src/config.py`
- Runtime orchestrator: `src/agent.py`
- Baseline comparator: `src/baseline.py`

This design separates baseline rule behavior from advanced model behavior so quality gains can be measured explicitly.

## Prompting & Quality Gates

The advanced agent uses prompt strategies and post-generation controls to improve reliability.

- Prompt strategies: `v1_basic`, `v2_structured`, `v3_rag_tools_cautious`
- Enforced response schema:
  - Summary
  - Likely Cause
  - Evidence
  - Next 3 Actions
  - Escalate If
  - Confidence
- Quality gate checks:
  - specificity
  - evidence citation presence
  - actionable step count
  - safety pass
- Regeneration policy: one repair pass if gate fails
- Weak evidence policy: explicitly indicate `Insufficient evidence`

## Tooling Strategy

Tools are used to enrich grounded operational reasoning beyond model prior knowledge.

- Tool execution/routing: `src/tools.py`
- Tool outputs are summarized and injected into model context
- Tool evidence can be cited in response body (for example `[Tool:...]` references)
- If tool results are missing or weak, the agent degrades safely and lowers confidence

## RAG Strategy

Retrieval is used to ground outputs in project knowledge.

- Canonical source format: PDF-only files in `data/knowledge/*.pdf`
- PDF ingestion: `PyPDFLoader` in `src/rag.py` and `src/build_rag_knowledge_base.py`
- Chunking strategy: recursive splitter with overlap
- Retrieval mode: semantic + lexical fallback hybrid
- Rebuild command:
  ```bash
  python -m src.build_rag_knowledge_base
  ```
- First-run requirement: build KB artifacts before normal query usage

## Safety & Failure Handling

The assistant is explicitly tuned for cautious AI Ops behavior.

- Blocks unsafe direct production-action language patterns
- Requires clearer caution under weak grounding
- Uses clarifying-question behavior for underspecified user prompts
- Provides fallback response on runtime failure with low-confidence framing
- Supports explicit escalation criteria in final output

## Packaging & Operations

The repository is structured for reproducible, check-in-safe operation.

- Frontend stack is HTML/CSS/JS for predictable deployment simplicity
- `.env.example` is committed; `.env` remains local-only
- Runtime/generated artifacts are excluded via `.gitignore`
- KB artifacts are rebuildable and not required to be committed

## Tradeoffs

- PDF-only source policy simplifies governance, but extraction quality depends on text layer quality.
- Scanned/image PDFs require OCR for reliable retrieval.
- Large corpora improve realism, but increase rebuild cost/time and retrieval-noise risk.
- Hybrid retrieval improves resilience, but adds pipeline complexity.

## Readiness Summary

The system is suitable for evaluator review as a phase-wise AI Ops copilot prototype with explicit LLM design, grounded retrieval, tool-assisted reasoning, safety guardrails, and reproducible operational workflow.
