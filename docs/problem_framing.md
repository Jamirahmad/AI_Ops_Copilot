# Problem Framing

## Primary User Persona

AI Ops / SRE on-call engineer responsible for incident triage, escalation, and mitigation coordination.

## Daily Workflow

1. Receive alert or incident signal.
2. Validate customer impact and blast radius.
3. Correlate logs, recent deploys, and service dependencies.
4. Decide immediate actions and escalation threshold.
5. Communicate confidence and next steps to responders.

## Exact Problem

During incidents, engineers lose time collecting fragmented context and producing consistent, safe, action-ready guidance.

## Product Goal

Provide a reliable copilot that turns incident questions into evidence-grounded, readable, and safe triage guidance with explicit next actions and escalation criteria.

## Current Knowledge Model

- Canonical knowledge source is PDF-only: `data/knowledge/*.pdf`.
- First-run prerequisite: build retrieval artifacts before usage:
  ```bash
  python -m src.build_rag_knowledge_base
  ```
- Retrieved context and tool outputs are combined for final response generation.

## Inputs

- User query (incident question)
- Conversation context and session memory
- Retrieved knowledge context (from PDF-derived chunks)
- Tool outputs (logs/deploy/dependency checks)

## Outputs

Structured response with:
- Summary
- Likely Cause
- Evidence
- Next 3 Actions
- Escalate If
- Confidence

## Constraints

- Must be evidence-grounded
- Must avoid unsafe production directives
- Must be readable under time pressure
- Must handle missing/weak evidence explicitly
- Must degrade safely when retrieval/tool evidence is weak

## Assumptions

- OpenRouter API access exists for model and embeddings
- PDF knowledge files contain extractable text layers
- Operational data schema remains stable
- Knowledge base artifacts are rebuilt when source PDFs change

## Example User Questions

1. Why are auth failures increasing after the latest deploy?
2. Using the troubleshooting docs, what should I check first for payment latency in ap-south?
3. Did rollback reduce checkout 5xx errors in the last 10 minutes?
4. What is the likely cause and next 3 actions for this alert burst?
5. When should I escalate this incident to incident command?

## Success Criteria

- Response is consistently structured and easy to scan
- Claims include evidence references
- Action list is concrete, bounded, and operationally safe
- Escalation threshold is explicit and time/impact-based
- Out-of-scope or weak-evidence cases clearly state `Insufficient evidence`

## Known Failure Cases / Edge Scenarios

- Low-quality PDF extraction (scanned docs without OCR)
- Ambiguous prompts requiring clarifying question
- Retrieval miss due vocabulary mismatch
- Tool output unavailable, delayed, or stale
- Overly broad incidents spanning unrelated services
- Very large corpora causing slower rebuilds or noisier retrieval
