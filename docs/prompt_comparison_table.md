# Prompt Comparison Table

## Goal

Compare prompt variants on the same PDF-relevant test set and identify the best default strategy.

## Variants Compared

- `v1_basic`: concise practical guidance with minimal structure pressure
- `v2_structured`: stronger structure and action orientation
- `v3_rag_tools_cautious`: evidence-grounded, safety-aware, weak-evidence explicit behavior

## Test Set (Same Inputs, PDF-Relevant)

1. `From ITOC_1.1_UG_Troubleshooting.pdf, what is the recommended triage flow for recurring authentication failures after a deployment?`
2. `Using troubleshooting.pdf and dqrl2mst.pdf context, what are the likely causes of payment latency spikes and the next 3 checks?`
3. `Based on MURAL-O_and_T-v4_2.pdf, when should an operator escalate an incident to incident command?`
4. `From G10356-01.pdf, summarize safe first-response actions for rising checkout 5xx errors without taking risky production steps.`

## Comparison Table

| Prompt Variant | Structure Quality | Evidence Grounding | Actionability | Safety Behavior | Weak-Evidence Handling | Overall |
|---|---|---|---|---|---|---|
| `v1_basic` | Low-Medium | Low | Medium | Medium | Low | Lowest |
| `v2_structured` | Medium-High | Medium | High | Medium-High | Medium | Better |
| `v3_rag_tools_cautious` | High | High | High | High | High | Best |

## Scenario-Level Notes

| Scenario | `v1_basic` | `v2_structured` | `v3_rag_tools_cautious` |
|---|---|---|---|
| ITOC auth triage flow | Generic steps, limited grounding | Better sequence and readability | Strongly grounded flow with clearer escalation and confidence framing |
| troubleshooting + dqrl2mst latency checks | Broad checklist, lower specificity | More concrete checks | Most specific actions tied to evidence and safer ordering |
| MURAL escalation criteria | May be vague about thresholds | Better threshold language | Most explicit escalation triggers and uncertainty signaling |
| G10356 safe 5xx response | Safety tone can be inconsistent | Better safe-action framing | Most reliable guardrails and no direct risky commands |

## Phase-Wise Prompt Evolution (Code-Aligned + Explicit Prompt)

| Phase | Prompt Snippet (Explicit) | What Was Added | Observed Improvement |
|---|---|---|---|
| Phase 2 | Baseline rules (no LLM prompt). Behavior is template/rule based in `src/baseline.py`. | Deterministic keyword routing | Fast but shallow responses; minimal grounding and nuance |
| Phase 3 (v1) | `Be concise and practical.` | Initial LLM prompt strategy (`v1_basic`) | Better fluency than baseline, but inconsistent structure |
| Phase 3 (v2) | `Use clear structure and action-oriented reasoning.` | Structured prompt strategy (`v2_structured`) | Better readability and clearer action flow |
| Phase 4-5 (v3 core) | `Ground claims in evidence and avoid operationally unsafe instructions. If evidence is weak, say 'Insufficient evidence'.` | Evidence/safety-forward strategy (`v3_rag_tools_cautious`) | Better grounding and safer operational posture |
| Phase 6-7 | Prompt context blocks include: `Conversation memory:` and `Adaptive instruction:` | Memory continuity + feedback-driven adaptation | Better multi-turn consistency and personalization |
| Phase 8-9 | Prompt requires exact headings: `Summary`, `Likely Cause`, `Evidence`, `Next 3 Actions`, `Escalate If`, `Confidence`; plus rules: `Never instruct immediate risky production actions.` | Strict schema + safety constraints + quality gate/repair | Most consistent, grader-friendly, and safe responses |

## Current Effective Prompt Shape (from `src/agent.py`)

Key enforced prompt instructions now include:

- `You are a senior AI Ops assistant with a calm, direct, human tone.`
- `You MUST include these exact headings as standalone lines:`
  - `Summary:`
  - `Likely Cause:`
  - `Evidence:`
  - `Next 3 Actions:`
  - `Escalate If:`
  - `Confidence:`
- `Evidence and actions must be bullet points.`
- `Next 3 Actions must have exactly 3 bullets.`
- `Never pretend certainty when evidence is weak.`
- `Never instruct immediate risky production actions.`

## Key Insights

1. Structure alone (`v2_structured`) improves readability and actionability, but evidence discipline remains mixed.
2. Evidence + safety constraints (`v3_rag_tools_cautious`) produce the most reliable ops-grade responses.
3. Weak-evidence handling is strongest in `v3`, reducing overconfident or speculative outputs.
4. Phase 8-9 schema enforcement is critical for consistent UI readability and evaluator scoring.

## Recommended Default

Use **`v3_rag_tools_cautious`** as the default prompt strategy.

Reason:
- Best balance of grounding, actionable triage output, and operational safety.
- Most consistent with strict response schema and evaluator expectations.

## How to Reproduce

- Ensure PDFs exist in `data/knowledge/*.pdf`
- Build KB first:
  ```bash
  python -m src.build_rag_knowledge_base
  ```
- Compare strategies:
  - `GET /compare_prompts?q=...`
- Cross-check evaluation summary:
  - `GET /evaluate`
