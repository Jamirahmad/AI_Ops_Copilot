def basic_agent(query: str) -> str:
    if "failure" in query.lower():
        return "Check system logs for failure spikes."
    elif "deployment" in query.lower():
        return "Review recent deployment history."
    elif "latency" in query.lower():
        return "Check service latency dashboards."
    else:
        return "Insufficient information. Please provide more details."
