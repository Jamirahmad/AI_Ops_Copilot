# Grader Phase Checklist

## Phase 2

- [ ] Baseline agent responds to simple incident questions
- [ ] Baseline limitations are documented

## Phase 3

- [ ] LLM integration uses OpenRouter-compatible API
- [ ] Prompt strategies are implemented and comparable
- [ ] Output quality gate/regeneration exists

## Phase 4

- [ ] Retrieval pipeline implemented (`src/rag.py`)
- [ ] Knowledge-base builder exists (`src/build_rag_knowledge_base.py`)
- [ ] Current knowledge source is PDF corpus (`data/knowledge/*.pdf`)
- [ ] Hybrid retrieval behavior present

## Phase 5

- [ ] At least two tools are defined and callable
- [ ] Tool output is integrated into final response
- [ ] Safeguards against unsafe guidance exist

## Phase 6

- [ ] Multi-turn memory is implemented
- [ ] Session reset behavior works
- [ ] Clarifying-question behavior exists

## Phase 7

- [ ] Feedback endpoint persists signals
- [ ] UI feedback controls present (thumbs)
- [ ] Adaptive instruction influences model prompt

## Phase 8

- [ ] API serves UI and core endpoints
- [ ] Error/loading states are visible in UI
- [ ] Logging artifacts are persisted

## Phase 9

- [ ] `/evaluate` returns structured comparisons
- [ ] Metrics include specificity/citations/actions/safety
- [ ] Failure modes and next-step risks are documented
