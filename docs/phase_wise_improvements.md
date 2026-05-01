# Phase-Wise Improvements (Phases 2-9)

## Phase 2: Basic Working Agent

- Built rule/template baseline (`src/baseline.py`)
- Added CLI/API invocation path
- Logged baseline outputs and limitations

## Phase 3: Smarter Agent (LLM)

- Integrated OpenRouter-compatible LLM (`src/agent.py`)
- Added prompt variants (`v1_basic`, `v2_structured`, `v3_rag_tools_cautious`)
- Added quality gate and one-pass regeneration

## Phase 4: Knowledge + Retrieval

- Added chunking + retrieval pipeline (`src/rag.py`)
- Added persisted knowledge base builder (`src/build_rag_knowledge_base.py`)
- Current source model: PDF corpus in `data/knowledge/*.pdf`
- Hybrid retrieval: semantic + lexical fallback

## Phase 5: Tool Usage

- Added tool routing/execution (`src/tools.py`)
- Integrated tool outputs into final response grounding
- Added guardrails around unsafe actions

## Phase 6: Planning, Memory, Context

- Added session memory (`src/memory.py`)
- Clarifying-question behavior for underspecified prompts
- Multi-turn continuity via `session_id`

## Phase 7: Adaptive Behavior

- Added feedback capture (`/feedback`, `src/feedback.py`)
- Thumbs UX mapped to adaptive instruction signal

## Phase 8: Deployment Readiness

- FastAPI service (`app.py`) with health/query/evaluate routes
- HTML/CSS/JS frontend (`frontend/`)
- Runtime and error logging paths under `data/`

## Phase 9: Evaluation & Review

- Built evaluation harness (`src/evaluation.py`)
- Added specificity/citation/action/safety metrics
- Baseline-vs-advanced structured comparison
