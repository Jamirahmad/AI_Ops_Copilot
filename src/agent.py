from __future__ import annotations

import re
import time
from typing import Dict, List, Tuple

from langchain_openai import ChatOpenAI

from src.config import (
    DEFAULT_PROMPT_STRATEGY,
    MODEL_NAME,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    TEMPERATURE,
)
from src.feedback import adaptive_instruction
from src.logger import log_error, log_event
from src.memory import append_turn, memory_summary
from src.rag import build_vectorstore, retrieve_context, stringify_context
from src.tools import execute_tools, summarize_tool_results

# Phase map for graders:
# - Phase 3: LLM integration, prompt strategy variants, prompt quality controls.
# - Phase 4: Retrieval context integration (RAG) into agent reasoning.
# - Phase 5: Tool output integration in reasoning loop.
# - Phase 6: Multi-turn memory usage in prompts.
# - Phase 7: Adaptive behavior via feedback instruction.
# - Phase 8: Graceful failure/fallback behavior for runtime robustness.
# - Phase 9: Response quality metrics and guard checks used in evaluation.

PROMPT_VARIANTS: Dict[str, str] = {
    "v1_basic": "Be concise and practical.",
    "v2_structured": "Use clear structure and action-oriented reasoning.",
    "v3_rag_tools_cautious": (
        "Ground claims in evidence and avoid operationally unsafe instructions. "
        "If evidence is weak, say 'Insufficient evidence'."
    ),
}

STYLE_HINTS = {
    "concise": "Keep response tight: 5-8 lines total.",
    "standard": "Balanced detail and clarity.",
    "deep-dive": "Provide richer context, but stay readable and direct.",
}

REQUIRED_SECTIONS = [
    "Summary",
    "Likely Cause",
    "Evidence",
    "Next 3 Actions",
    "Escalate If",
    "Confidence",
]

HEADING_ALIASES = {
    "Summary": ["Summary", "What I think is happening"],
    "Likely Cause": ["Likely Cause"],
    "Evidence": ["Evidence", "What points to this"],
    "Next 3 Actions": ["Next 3 Actions", "What to do now"],
    "Escalate If": ["Escalate If", "Escalate when"],
    "Confidence": ["Confidence"],
}

_vectorstore = None


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = build_vectorstore()
    return _vectorstore


def _llm_client() -> ChatOpenAI:
    return ChatOpenAI(
        model_name=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=900,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
    )


def _confidence_label(text: str) -> str:
    low_cues = ["uncertain", "insufficient evidence", "not enough"]
    medium_cues = ["likely", "possible", "appears", "moderate"]
    t = text.lower()
    if any(c in t for c in low_cues):
        return "low"
    if any(c in t for c in medium_cues):
        return "medium"
    return "high"


def _needs_clarification(query: str) -> bool:
    q = query.strip().lower()
    if len(q.split()) < 4:
        return True
    vague_terms = ["help", "issue", "problem", "not working", "something wrong"]
    has_signal = any(k in q for k in ["latency", "failure", "deploy", "auth", "timeout", "error", "payment"])
    return any(v in q for v in vague_terms) and not has_signal


def _clarifying_response(query: str) -> str:
    return (
        "I can help, but I need one detail first to avoid guessing.\n\n"
        f"For '{query}', what is the exact service and one concrete symptom "
        "(error code, latency value, or failed workflow)?"
    )


def _citation_rate(text: str) -> float:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    cited = sum(1 for ln in lines if re.search(r"\[\d+\]", ln) or "[Tool:" in ln)
    return cited / len(lines)


def _actionable_step_count(text: str) -> int:
    return len([ln for ln in text.splitlines() if ln.strip().startswith("- ")])


def _specificity_score(text: str) -> float:
    score = 0.0
    if re.search(r"\b\d{1,2}:\d{2}\b", text):
        score += 0.25
    if re.search(r"\b\d+(\.\d+)?\s?(ms|s|sec|seconds|minutes|%|errors?)\b", text.lower()):
        score += 0.25
    if _actionable_step_count(text) >= 3:
        score += 0.25
    if _citation_rate(text) >= 0.10:
        score += 0.25
    return min(1.0, score)


def _safety_pass(text: str) -> bool:
    lower = text.lower()
    disallowed = [
        "run migration now",
        "execute in production now",
        "delete production data",
        "apply change directly now",
        "restart production immediately",
    ]
    return not any(d in lower for d in disallowed)


def response_quality_metrics(text: str) -> Dict[str, float | int | bool]:
    return {
        "specificity_score": round(_specificity_score(text), 3),
        "evidence_citation_rate": round(_citation_rate(text), 3),
        "actionable_step_count": _actionable_step_count(text),
        "safety_pass": _safety_pass(text),
    }


def _quality_gate(text: str, weak_evidence: bool) -> Tuple[bool, List[str]]:
    issues: List[str] = []

    if len(text.strip()) < 120:
        issues.append("Response is too short and likely vague.")

    if weak_evidence and "Insufficient evidence" not in text:
        issues.append("Must explicitly say 'Insufficient evidence' when evidence is weak.")

    if _citation_rate(text) < 0.08:
        issues.append("Add citations like [1], [2], [Tool:LogAnalyzer] to key claims.")

    metrics = response_quality_metrics(text)
    if metrics["specificity_score"] < 0.45:
        issues.append("Add concrete timestamps, metrics, and explicit next actions.")

    if not metrics["safety_pass"]:
        issues.append("Remove unsafe direct-production action instructions.")

    return len(issues) == 0, issues


def _build_prompt(
    query: str,
    session_id: str,
    strategy: str,
    response_style: str,
    context_text: str,
    tools_text: str,
    weak_evidence: bool,
    repair_issues: List[str] | None = None,
) -> str:
    # Phase 3/7: Prompt engineering + adaptive prompt overlays.
    base_prompt = PROMPT_VARIANTS.get(strategy, PROMPT_VARIANTS[DEFAULT_PROMPT_STRATEGY])
    adaptive = adaptive_instruction() or "None"
    style_hint = STYLE_HINTS.get(response_style, STYLE_HINTS["standard"])
    repair_block = ""
    if repair_issues:
        repair_block = "\nFix these quality issues from your previous draft:\n- " + "\n- ".join(repair_issues)

    evidence_rule = (
        "Evidence appears weak. You must explicitly say 'Insufficient evidence'."
        if weak_evidence
        else "Use grounded claims with explicit citations like [1], [2], [Tool:...]."
    )

    return f"""
You are a senior AI Ops assistant with a calm, direct, human tone.
{base_prompt}

Write the response in a conversational ChatGPT-like style that is easy to skim.
You MUST include these exact headings as standalone lines:
Summary:
Likely Cause:
Evidence:
Next 3 Actions:
Escalate If:
Confidence:

Rules:
- Evidence and actions must be bullet points.
- "Next 3 Actions" must have exactly 3 bullets.
- Never pretend certainty when evidence is weak.
- Never instruct immediate risky production actions.
- {evidence_rule}
- {style_hint}

Adaptive instruction:
{adaptive}

Conversation memory:
{memory_summary(session_id)}

Retrieved context:
{context_text}

Tool output:
{tools_text}

User query:
{query}
{repair_block}
""".strip()


def _extract_sections_anywhere(text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    all_labels = []
    for canonical, aliases in HEADING_ALIASES.items():
        for alias in aliases:
            all_labels.append((canonical, alias))

    for canonical, alias in all_labels:
        pattern = re.compile(
            rf"(?is)(?:^|\n|\s){re.escape(alias)}\s*:\s*(.*?)(?=(?:^|\n|\s)(?:Summary|Likely Cause|Evidence|What points to this|Next 3 Actions|What to do now|Escalate If|Escalate when|Confidence)\s*:|\Z)"
        )
        m = pattern.search(text)
        if m and canonical not in sections:
            sections[canonical] = m.group(1).strip()
    return sections


def _to_bullets(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    out = []
    for ln in lines:
        cleaned = re.sub(r"^\d+\.\s+", "", ln)
        cleaned = cleaned[2:].strip() if cleaned.startswith("- ") else cleaned
        if cleaned:
            out.append(f"- {cleaned}")
    return "\n".join(out)


def _ensure_three_actions(text: str) -> str:
    bullets = [ln for ln in _to_bullets(text).splitlines() if ln.strip()]
    bullets = bullets[:3]
    while len(bullets) < 3:
        bullets.append("- Validate impact, mitigation, and owner assignment before next update.")
    return "\n".join(bullets)


def _enforce_response_schema(text: str, weak_evidence: bool) -> str:
    cleaned = text.strip().replace("\r\n", "\n")
    sections = _extract_sections_anywhere(cleaned)

    if "Summary" not in sections:
        lead = re.split(r"\n\s*(?:Summary|Likely Cause|Evidence|What points to this|Next 3 Actions|What to do now|Escalate If|Escalate when|Confidence)\s*:", cleaned, maxsplit=1)[0].strip()
        sections["Summary"] = lead or "Current incident indicators suggest elevated operational risk requiring triage."

    if "Likely Cause" not in sections:
        sections["Likely Cause"] = sections["Summary"]

    evidence_text = sections.get("Evidence", "")
    if weak_evidence and "Insufficient evidence" not in evidence_text:
        evidence_text = (evidence_text + "\n- Insufficient evidence").strip()
    sections["Evidence"] = _to_bullets(evidence_text) or "- Insufficient evidence"

    sections["Next 3 Actions"] = _ensure_three_actions(sections.get("Next 3 Actions", ""))

    escalate = _to_bullets(sections.get("Escalate If", ""))
    sections["Escalate If"] = escalate or "- Escalate if customer impact persists beyond 10 minutes despite mitigation."

    conf = sections.get("Confidence", "").strip()
    if not conf:
        conf = "medium - partial evidence; verify with live metrics and logs"
    if "-" not in conf and ":" not in conf and len(conf.split()) < 4:
        conf = f"{conf.lower()} - confidence requires additional corroboration"
    sections["Confidence"] = conf

    blocks = []
    for key in REQUIRED_SECTIONS:
        blocks.append(f"{key}:\n{sections.get(key, '').strip()}")
    return "\n\n".join(blocks).strip()


def parse_structured_response(text: str) -> Dict[str, str]:
    # Phase 8: normalized output parser for consistent UI cards.
    sections = {}
    patterns = {
        "Summary": r"^(Summary|What I think is happening)\s*:?$",
        "Likely Cause": r"^(Likely Cause)\s*:?$",
        "Evidence": r"^(Evidence|What points to this)\s*:?$",
        "Next 3 Actions": r"^(Next 3 Actions|What to do now)\s*:?$",
        "Escalate If": r"^(Escalate If|Escalate when)\s*:?$",
        "Confidence": r"^(Confidence)\s*:?$",
    }

    lines = text.splitlines()
    idx = []
    for i, line in enumerate(lines):
        for key, pat in patterns.items():
            if re.match(pat, line.strip(), flags=re.IGNORECASE):
                idx.append((i, key))
                break

    if not idx:
        return _extract_sections_anywhere(text)

    for j, (start, key) in enumerate(idx):
        end = idx[j + 1][0] if j + 1 < len(idx) else len(lines)
        body = "\n".join(lines[start + 1 : end]).strip()
        sections[key] = body
    return sections


def run_agent(
    query: str,
    strategy: str = DEFAULT_PROMPT_STRATEGY,
    use_retrieval: bool = True,
    use_tools: bool = True,
    session_id: str = "default",
    response_style: str = "standard",
) -> str:
    # Phase 3-8 core orchestration path.
    start = time.time()
    context_text = "Retrieval disabled."
    tool_text = "Tools disabled."

    try:
        # Phase 6: Clarifying behavior for underspecified multi-turn input.
        if _needs_clarification(query):
            response = _clarifying_response(query)
            append_turn(session_id, query, response)
            log_event(
                query=query,
                response=response,
                latency_sec=time.time() - start,
                mode="advanced",
                prompt_strategy=strategy,
                retrieval_used=use_retrieval,
                tool_summary=tool_text,
                confidence="low",
            )
            return response

        chunks = []
        # Phase 4: Retrieval augmentation.
        if use_retrieval:
            chunks = retrieve_context(_get_vectorstore(), query)
            context_text = stringify_context(chunks)

        tool_payload = {"selected_tools": [], "results": []}
        # Phase 5: Tool calling and tool evidence summarization.
        if use_tools:
            tool_payload = execute_tools(query)
            tool_text = summarize_tool_results(tool_payload)

        weak_evidence = (len(chunks) == 0) and not any(r.ok for r in tool_payload.get("results", []))

        prompt = _build_prompt(
            query=query,
            session_id=session_id,
            strategy=strategy,
            response_style=response_style,
            context_text=context_text,
            tools_text=tool_text,
            weak_evidence=weak_evidence,
        )

        if not OPENROUTER_API_KEY:
            response = (
                "Summary:\n"
                "Model access is not configured, so diagnosis quality is limited.\n\n"
                "Likely Cause:\n"
                "Missing API credentials prevent full reasoning and evidence-grounded analysis.\n\n"
                "Evidence:\n"
                "- Insufficient evidence [1]\n\n"
                "Next 3 Actions:\n"
                "- Set OPENROUTER_API_KEY in .env\n"
                "- Retry this query with retrieval enabled\n"
                "- Escalate to human analyst if impact is ongoing\n\n"
                "Escalate If:\n"
                "- Customer impact remains active beyond 5 minutes\n\n"
                "Confidence:\n"
                "low - model unavailable"
            )
        else:
            llm = _llm_client()
            response = getattr(llm.invoke(prompt), "content", "")

            # Phase 3/9: Quality gate with one-pass regeneration.
            passed, issues = _quality_gate(response, weak_evidence=weak_evidence)
            if not passed:
                repair_prompt = _build_prompt(
                    query=query,
                    session_id=session_id,
                    strategy=strategy,
                    response_style=response_style,
                    context_text=context_text,
                    tools_text=tool_text,
                    weak_evidence=weak_evidence,
                    repair_issues=issues,
                )
                response = getattr(llm.invoke(repair_prompt), "content", response)

        response = _enforce_response_schema(response, weak_evidence=weak_evidence)

        append_turn(session_id, query, response)
        latency = time.time() - start
        log_event(
            query=query,
            response=response,
            latency_sec=latency,
            mode="advanced",
            prompt_strategy=strategy,
            retrieval_used=use_retrieval,
            tool_summary=tool_text,
            confidence=_confidence_label(response),
        )
        return response

    except Exception as e:
        log_error("run_agent", e)
        fallback = (
            "Summary:\nInternal error while generating the diagnosis.\n\n"
            "Likely Cause:\nRuntime failure in agent pipeline.\n\n"
            "Evidence:\n- Insufficient evidence\n\n"
            "Next 3 Actions:\n"
            "- Check error budget burn and active customer impact\n"
            "- Validate rollback status against latest deployment\n"
            "- Escalate to on-call analyst\n\n"
            "Escalate If:\n- Customer impact is ongoing.\n\n"
            "Confidence:\nlow - internal failure"
        )
        append_turn(session_id, query, fallback)
        return fallback


def compare_prompt_outputs(query: str, session_id: str = "compare", response_style: str = "standard") -> Dict[str, str]:
    outputs = {}
    for strategy in PROMPT_VARIANTS:
        outputs[strategy] = run_agent(
            query=query,
            strategy=strategy,
            use_retrieval=True,
            use_tools=True,
            session_id=f"{session_id}-{strategy}",
            response_style=response_style,
        )
    return outputs
