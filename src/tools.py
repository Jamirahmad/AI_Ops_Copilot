from langchain.tools import Tool

def analyze_logs(query: str) -> str:
    return "Detected spike in authorization failures between 10–11 AM."

def check_deployment(_: str) -> str:
    return "Deployment at 10 AM impacted TS2 authorization module."

tools = [
    Tool(
        name="LogAnalyzer",
        func=analyze_logs,
        description="Analyze logs for failures and anomalies"
    ),
    Tool(
        name="DeploymentChecker",
        func=check_deployment,
        description="Check recent deployments"
    )
]
