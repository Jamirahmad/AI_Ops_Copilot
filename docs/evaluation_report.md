# Evaluation Report

## Scope

Evaluate baseline vs advanced AI Ops assistant quality for incident triage use cases under the current production-style configuration.

## Evaluation Preconditions

1. Ensure knowledge PDFs are present in `data/knowledge/*.pdf`.
2. Build retrieval artifacts before evaluation:
   ```bash
   python -m src.build_rag_knowledge_base
   ```
3. Run API and execute `GET /evaluate`.

## Method

- Run predefined scenarios via `/evaluate`.
- Compare baseline and advanced outputs.
- Measure:
  - specificity score
  - evidence citation rate
  - actionable step count
  - safety pass rate

## Key Findings

1. Advanced mode consistently outperforms baseline on structure and actionability.
2. Evidence-grounding improves when retrieval and tools are available.
3. Safety posture is stronger in advanced mode due to schema enforcement, quality gate checks, and cautious prompting.
4. Structured response schema improves readability and operational usability in the UI.

## Current Data Context

- Canonical knowledge source is PDF-only: `data/knowledge/*.pdf`.
- Retrieval artifacts are generated into `data/knowledge_base/`.
- Large synthetic operational datasets are available for stress-testing retrieval and response consistency.

## Observed Failure Modes

- Retrieval misses when relevant facts are poorly extracted from PDFs.
- Out-of-scope prompts can still produce low-confidence guidance, but should explicitly indicate weak grounding (for example, `Insufficient evidence`).
- Very large corpora increase rebuild/runtime cost and can reduce retrieval precision without tighter filtering.

## Product/UX Notes from Evaluation

- Responses are enforced into a strict section schema:
  - Summary
  - Likely Cause
  - Evidence
  - Next 3 Actions
  - Escalate If
  - Confidence
- `Helpful?` thumbs feedback appears only after response completion and is logged for adaptive behavior.

## Residual Risks

- PDF extraction quality varies by source formatting and text layer availability.
- Image-only/scanned PDFs require OCR to avoid grounding gaps.
- Ambiguous prompts still require clarifying-question loops.

## Recommended Next Steps

1. Add OCR support for scanned/image-only PDFs.
2. Add retrieval diagnostics (top-k source quality and citation coverage tracking).
3. Add periodic KB rebuild + smoke evaluation automation.
4. Add query-time scope detection to reduce low-value responses for unsupported domains.
