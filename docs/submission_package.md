# Submission Package Index

## Core App

- Backend entrypoint: `app.py`
- Frontend: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`

## Source Modules

- Agent orchestration: `src/agent.py`
- Baseline: `src/baseline.py`
- Retrieval: `src/rag.py`
- KB builder: `src/build_rag_knowledge_base.py`
- Tools: `src/tools.py`
- Evaluation harness: `src/evaluation.py`
- Demo runner: `src/demo_runner.py`

## Documentation

- Problem framing: `docs/problem_framing.md`
- Phase improvements: `docs/phase_wise_improvements.md`
- Grader checklist: `docs/grader_phase_checklist.md`
- Evaluation report: `docs/evaluation_report.md`
- Engineering/product justification: `docs/engineering_product_justification.md`
- Demo script: `demo/demo_script.md`

## Knowledge & Data

- Knowledge source (current): `data/knowledge/*.pdf`
- KB artifacts: `data/knowledge_base/`
- Scale data generator: `scripts/generate_test_data.ps1`

## Run Commands

```bash
uvicorn app:app --reload
python -m src.build_rag_knowledge_base
python src/demo_runner.py
```

## Notes

- Install dependencies first: `pip install -r requirements.txt`
- Ensure OpenRouter keys are configured in `.env`
