test_queries = [
    "Why are transaction failures increasing?",
    "Did deployment impact TS2?",
    "What caused latency spike?"
]

def evaluate(agent_func):
    results = []

    for q in test_queries:
        response = agent_func(q)

        results.append({
            "query": q,
            "response": response,
            "relevance": "Manual check",
            "safety": "Check refusal/escalation"
        })

    return results
