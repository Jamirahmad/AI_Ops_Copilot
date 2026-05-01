from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.agent import compare_prompt_outputs, parse_structured_response, response_quality_metrics, run_agent
from src.baseline import basic_agent
from src.evaluation import run_phase_evaluation
from src.feedback import store_feedback
from src.memory import reset_memory

# Phase map for graders (project phases 2-9):
# - Phase 2: /baseline endpoint for rules/template agent.
# - Phase 3: /query and /compare_prompts expose LLM + prompt strategies.
# - Phase 6: /memory/reset for memory retention/reset behavior.
# - Phase 7: /feedback for adaptive signal collection.
# - Phase 8: FastAPI deployment entrypoint + health + static UI serving.
# - Phase 9: /evaluate endpoint for evaluation harness and metrics review.
app = FastAPI(title="AI Ops Copilot", version="2.0")
FRONTEND_DIR = Path(__file__).parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"status": "frontend not found"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/baseline")
def baseline(q: str):
    return {"response": basic_agent(q)}


@app.get("/query")
def query(
    q: str,
    strategy: str = "v3_rag_tools_cautious",
    retrieval: bool = True,
    tools: bool = True,
    session_id: str = "default",
    response_style: str = "standard",
):
    response = run_agent(
        query=q,
        strategy=strategy,
        use_retrieval=retrieval,
        use_tools=tools,
        session_id=session_id,
        response_style=response_style,
    )
    return {
        "response": response,
        "sections": parse_structured_response(response),
        "quality": response_quality_metrics(response),
    }


@app.get("/query_stream")
async def query_stream(
    q: str,
    strategy: str = "v3_rag_tools_cautious",
    retrieval: bool = True,
    tools: bool = True,
    session_id: str = "default",
    response_style: str = "standard",
):
    response = run_agent(
        query=q,
        strategy=strategy,
        use_retrieval=retrieval,
        use_tools=tools,
        session_id=session_id,
        response_style=response_style,
    )

    async def event_generator():
        words = response.split()
        for word in words:
            payload = {"chunk": f"{word} "}
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.01)

        yield f"data: {json.dumps({'sections': parse_structured_response(response)})}\n\n"
        yield f"data: {json.dumps({'quality': response_quality_metrics(response)})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/compare_prompts")
def compare_prompts(q: str, session_id: str = "compare", response_style: str = "standard"):
    return compare_prompt_outputs(query=q, session_id=session_id, response_style=response_style)


@app.post("/feedback")
def feedback(q: str, rating: int, notes: str = "", session_id: str = "default"):
    record = store_feedback(q, rating, notes=notes, session_id=session_id)
    return {"status": "feedback recorded", "record": record}


@app.post("/memory/reset")
def memory_reset(session_id: str = ""):
    reset_memory(session_id or None)
    return {"status": "memory reset", "session_id": session_id or "all"}


@app.get("/evaluate")
def evaluate():
    return run_phase_evaluation()
