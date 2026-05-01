# Evaluation Report

## Scope

Evaluate baseline vs advanced AI Ops assistant quality for incident triage use cases.

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
2. Evidence-grounding improves when retrieval + tools are available.
3. Safety posture is stronger in advanced mode due to explicit prompt and quality checks.

## Current Data Context

- Knowledge source has been standardized to PDF documents in `data/knowledge/`.
- Large synthetic operational datasets are available for stress-testing retrieval and evaluation scenarios.

## Residual Risks

- PDF extraction quality may vary by document format.
- Very large corpora can increase rebuild cost/time.
- Ambiguous prompts still require user clarification loops.

## Recommended Next Steps

1. Add OCR path for image-only PDFs.
2. Add retrieval diagnostics (top-k source quality reporting).
3. Add automated periodic KB rebuild + smoke evaluation.
