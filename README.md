# AI Ops Copilot

Python project implementing an incident-triage AI agent across phases 2-9.

## Setup

1. Create and activate your Python environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure `.env`:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   OPENROUTER_MODEL=openai/gpt-4o-mini
   OPENROUTER_EMBEDDING_MODEL=text-embedding-3-small
   DEFAULT_PROMPT_STRATEGY=v3_rag_tools_cautious
   ```


## First Run (Required Before Uvicorn)

If this is your first run (or after deleting `data/knowledge_base/`), build the RAG knowledge base first:

```bash
python -m src.build_rag_knowledge_base
```

This generates retrieval artifacts used by the agent at runtime.
## Run API + UI

```bash
uvicorn app:app --reload
```

Open UI at `http://127.0.0.1:8000/`.

## Core Endpoints

- `GET /health`
- `GET /baseline?q=...`
- `GET /query?q=...&strategy=v3_rag_tools_cautious&retrieval=true&tools=true&session_id=demo`
- `GET /query_stream?q=...&strategy=...&retrieval=true&tools=true&session_id=demo`
- `GET /compare_prompts?q=...`
- `POST /feedback?q=...&rating=4&notes=...&session_id=demo`
- `POST /memory/reset?session_id=demo`
- `GET /evaluate`

## UI (Current)

Current frontend is HTML/CSS/JS in `frontend/`.

Included UX:
- chat input + response panel
- session create/switch/reset/delete
- thumbs up/down feedback under completed assistant responses
- loading/error/retry states
- evaluation tab rendering `/evaluate` output

## RAG Knowledge Source (Current)

Knowledge source is now **PDF-only** inside:

- `data/knowledge/*.pdf`

Older `data/knowledge/*` subfolders were removed by design.

## Build RAG Knowledge Base

Rebuild chunks + metadata (+ optional FAISS):

```bash
python -m src.build_rag_knowledge_base
```

Artifacts:
- `data/knowledge_base/manifest.json`
- `data/knowledge_base/chunks.jsonl`
- `data/knowledge_base/stats.json`
- `data/knowledge_base/faiss_index/` (when embeddings run)

## Large Synthetic Test Data

Generator script:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\generate_test_data.ps1 -IncidentRows 1000000 -AlertRows 1000000 -MetricRows 1000000
```

This creates large-scale JSONL corpora for realistic retrieval/evaluation pressure testing.

## Deliverables

- Problem Framing: `docs/problem_framing.md`
- Demo Script: `demo/demo_script.md`
- Evaluation Report: `docs/evaluation_report.md`
- Engineering & Product Justification: `docs/engineering_product_justification.md`
- Phase-Wise Improvements: `docs/phase_wise_improvements.md`
- Grader Checklist: `docs/grader_phase_checklist.md`
- Submission Index: `docs/submission_package.md`


