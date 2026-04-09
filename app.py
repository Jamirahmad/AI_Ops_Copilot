from fastapi import FastAPI
from src.agent import run_agent
from src.feedback import store_feedback

app = FastAPI()

@app.get("/query")
def query(q: str):
    return {"response": run_agent(q)}

@app.post("/feedback")
def feedback(q: str, rating: int):
    store_feedback(q, rating)
    return {"status": "feedback recorded"}
