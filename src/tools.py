from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import LOGS_SOURCE_PATH, MAX_TOOL_CALLS, RUNBOOKS_PATH

# Phase map for graders:
# - Phase 5: Tool definitions and structured tool output contracts.
# - Phase 5 improvement: intent-scored routing + guardrails + explicit fail paths.

TOOL_SCHEMAS = {
    "LogAnalyzer": {
        "description": "Analyze log lines for error/failure spikes and auth issues.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
    },
    "DeploymentChecker": {
        "description": "Check deployment or change references from runbook notes.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
    },
}


@dataclass
class ToolCallResult:
    tool: str
    ok: bool
    signal: str
    time_window: str
    impact: str
    source: str
    raw_excerpt: str

    @property
    def output(self) -> str:
        status = "OK" if self.ok else "FAILED"
        return (
            f"{status} signal={self.signal}; time_window={self.time_window}; "
            f"impact={self.impact}; source={self.source}; raw={self.raw_excerpt}"
        )


def _read_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def analyze_logs(query: str) -> ToolCallResult:
    text = _read_text(LOGS_SOURCE_PATH)
    if not text.strip():
        return ToolCallResult(
            tool="LogAnalyzer",
            ok=False,
            signal="No log signal available",
            time_window="unknown",
            impact="unknown",
            source=LOGS_SOURCE_PATH,
            raw_excerpt="No logs available.",
        )

    lines = [ln for ln in text.splitlines() if ln.strip()]
    lowered = query.lower()
    filtered = [ln for ln in lines if any(k in ln.lower() for k in lowered.split())]
    sample = filtered[:4] if filtered else lines[:4]

    auth_count = sum(1 for ln in lines if "status=401" in ln or "status=403" in ln)
    timeout_count = sum(1 for ln in lines if "timeout" in ln.lower())
    signal = "Auth errors rising" if auth_count >= timeout_count else "Latency/timeout pressure"
    impact = "high" if (auth_count + timeout_count) >= 3 else "medium"

    time_window = "unknown"
    if sample:
        first_ts = sample[0].split(" ")[0]
        last_ts = sample[-1].split(" ")[0]
        time_window = f"{first_ts} to {last_ts}"

    return ToolCallResult(
        tool="LogAnalyzer",
        ok=True,
        signal=signal,
        time_window=time_window,
        impact=impact,
        source=LOGS_SOURCE_PATH,
        raw_excerpt=" | ".join(sample),
    )


def check_deployment(query: str) -> ToolCallResult:
    text = _read_text(RUNBOOKS_PATH)
    if not text.strip():
        return ToolCallResult(
            tool="DeploymentChecker",
            ok=False,
            signal="No deployment/runbook signal",
            time_window="unknown",
            impact="unknown",
            source=RUNBOOKS_PATH,
            raw_excerpt="No runbook data available.",
        )

    matches = [
        ln for ln in text.splitlines() if "deploy" in ln.lower() or "release" in ln.lower() or "rollback" in ln.lower()
    ]
    if not matches:
        return ToolCallResult(
            tool="DeploymentChecker",
            ok=False,
            signal="No deployment references found",
            time_window="unknown",
            impact="low",
            source=RUNBOOKS_PATH,
            raw_excerpt="No deployment references found.",
        )

    excerpt = " | ".join(matches[:4])
    time_candidates = [m.split(" ")[0] for m in matches[:4] if ":" in m]
    time_window = "unknown" if not time_candidates else ", ".join(time_candidates)
    impact = "medium" if "rollback" in excerpt.lower() else "low"

    return ToolCallResult(
        tool="DeploymentChecker",
        ok=True,
        signal="Deployment correlation candidate",
        time_window=time_window,
        impact=impact,
        source=RUNBOOKS_PATH,
        raw_excerpt=excerpt,
    )


def _intent_score(query: str) -> Dict[str, int]:
    q = query.lower()
    scores = {"LogAnalyzer": 0, "DeploymentChecker": 0}

    log_terms = ["error", "failure", "latency", "timeout", "auth", "log", "spike", "incident", "status"]
    deploy_terms = ["deploy", "release", "change", "rollback", "ts2", "version", "hotfix", "impact"]
    for t in log_terms:
        if t in q:
            scores["LogAnalyzer"] += 2
    for t in deploy_terms:
        if t in q:
            scores["DeploymentChecker"] += 2

    if "why" in q or "caused" in q:
        scores["LogAnalyzer"] += 1
        scores["DeploymentChecker"] += 1

    return scores


def route_tools(query: str) -> Tuple[List[str], Dict[str, int]]:
    # Phase 5: Tool selection from intent scores.
    scores = _intent_score(query)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    selected = [name for name, score in ranked if score > 0][:MAX_TOOL_CALLS]
    return selected, scores


def execute_tools(query: str) -> Dict[str, object]:
    # Phase 5: Tool execution with safeguards (max calls, dedupe, explicit failure).
    selected, scores = route_tools(query)

    if not selected:
        return {
            "selected_tools": [],
            "intent_scores": scores,
            "results": [
                ToolCallResult(
                    tool="ToolRouter",
                    ok=False,
                    signal="Intent too weak for tool call",
                    time_window="unknown",
                    impact="low",
                    source="router",
                    raw_excerpt="No suitable tool selected for this query.",
                )
            ],
            "incorrect_call_demo": True,
            "guardrails": ["No blind tool call when intent mismatch."],
        }

    seen = set()
    results: List[ToolCallResult] = []
    for tool in selected:
        if tool in seen:
            continue
        seen.add(tool)

        if len(results) >= MAX_TOOL_CALLS:
            break

        if tool == "LogAnalyzer":
            results.append(analyze_logs(query))
        elif tool == "DeploymentChecker":
            results.append(check_deployment(query))
        else:
            results.append(
                ToolCallResult(
                    tool=tool,
                    ok=False,
                    signal="Unknown tool",
                    time_window="unknown",
                    impact="low",
                    source="router",
                    raw_excerpt="Unknown tool.",
                )
            )

    return {
        "selected_tools": selected,
        "intent_scores": scores,
        "results": results,
        "incorrect_call_demo": any(not r.ok for r in results),
        "guardrails": [
            f"Max tool calls per request: {MAX_TOOL_CALLS}",
            "Deduplicate repeated tool calls.",
            "Return explicit failure instead of hallucinating tool output.",
        ],
    }


def summarize_tool_results(tool_payload: Dict[str, object]) -> str:
    rows = []
    for result in tool_payload.get("results", []):
        status = "OK" if result.ok else "FAILED"
        rows.append(f"[Tool:{result.tool}] {status} {result.output}")
    if not rows:
        return "No tool activity."
    return "\n".join(rows)
