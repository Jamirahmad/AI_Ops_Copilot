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

## Inputs

- User query (incident question)
- Conversation context
- Retrieved knowledge context (PDF corpus)
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

## Assumptions

- OpenRouter API access exists for model + embeddings
- PDF knowledge files contain extractable text
- Operational data schema remains stable

## Example User Questions

1. Why are auth failures increasing after the latest deploy?
2. What should I check first for payment latency spike in ap-south?
3. Did rollback reduce checkout 5xx errors in the last 10 minutes?
4. What is the likely cause and next 3 actions for this alert burst?
5. When should I escalate this incident to incident command?

## Success Criteria

- Response is structured and easy to scan
- Claims include evidence references
- Action list is concrete and bounded
- Escalation threshold is explicit
- Safety checks prevent harmful instructions

## Known Failure Cases / Edge Scenarios

- Low-quality PDF extraction (scanned docs without OCR)
- Ambiguous prompts requiring clarifying question
- Retrieval miss due vocabulary mismatch
- Tool output unavailable or stale
- Overly broad incidents spanning multiple unrelated services
