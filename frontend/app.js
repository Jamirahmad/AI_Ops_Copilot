const storeKey = "aiops_ui_store_v4";

// Phase map for graders:
// - Phase 6: Session state, multi-turn memory UX, reset handling.
// - Phase 7: Thumbs feedback capture and backend feedback submission.
// - Phase 8: Production-style UX states (loading/error/retry) + streaming UX.
// - Phase 9: Evaluation tab rendering metrics from /evaluate.

const state = {
  sessions: {},
  currentSessionId: null,
  lastRequest: null,
  generating: false,
};

const REQUIRED_SECTIONS = [
  "Summary",
  "Likely Cause",
  "Evidence",
  "Next 3 Actions",
  "Escalate If",
  "Confidence",
];

// Locked "most mature" defaults for end-users.
const ASSISTANT_DEFAULTS = {
  mode: "advanced",
  strategy: "v3_rag_tools_cautious",
  retrieval: true,
  tools: true,
  stream: true,
  responseStyle: "deep-dive",
};

const el = {
  sessionsList: document.getElementById("sessionsList"),
  newSessionBtn: document.getElementById("newSessionBtn"),
  messages: document.getElementById("messages"),
  queryInput: document.getElementById("queryInput"),
  sendBtn: document.getElementById("sendBtn"),
  retryBtn: document.getElementById("retryBtn"),
  spinner: document.getElementById("spinner"),
  errorBanner: document.getElementById("errorBanner"),
  chatTabBtn: document.getElementById("chatTabBtn"),
  evalTabBtn: document.getElementById("evalTabBtn"),
  chatTab: document.getElementById("chatTab"),
  evalTab: document.getElementById("evalTab"),
  runEvalBtn: document.getElementById("runEvalBtn"),
  evalSpinner: document.getElementById("evalSpinner"),
  evalOutput: document.getElementById("evalOutput"),
  toast: document.getElementById("toast"),
};

function safeNowId() {
  return "s-" + Date.now();
}

function saveState() {
  localStorage.setItem(
    storeKey,
    JSON.stringify({ sessions: state.sessions, currentSessionId: state.currentSessionId })
  );
}

function loadState() {
  try {
    const raw = localStorage.getItem(storeKey);
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    state.sessions = parsed.sessions || {};
    state.currentSessionId = parsed.currentSessionId || null;
    return true;
  } catch {
    return false;
  }
}

function createSession(name) {
  const id = safeNowId();
  state.sessions[id] = {
    id,
    name: name || `Session ${Object.keys(state.sessions).length + 1}`,
    messages: [],
  };
  state.currentSessionId = id;
  saveState();
}

function currentSession() {
  return state.sessions[state.currentSessionId];
}

function switchSession(id) {
  if (!state.sessions[id]) return;
  state.currentSessionId = id;
  saveState();
  renderSessions();
  renderMessages();
}

async function deleteSession(sessionId) {
  const target = state.sessions[sessionId];
  if (!target) return;

  const ok = window.confirm(`Delete session '${target.name}'? This cannot be undone.`);
  if (!ok) return;

  try {
    await fetch(`/memory/reset?session_id=${encodeURIComponent(sessionId)}`, { method: "POST" });
  } catch {
    // Ignore backend reset failures and proceed with local delete.
  }

  delete state.sessions[sessionId];

  if (Object.keys(state.sessions).length === 0) {
    createSession("Session 1");
  } else if (state.currentSessionId === sessionId) {
    state.currentSessionId = Object.keys(state.sessions)[0];
  }

  saveState();
  renderSessions();
  renderMessages();
  showToast("Session deleted");
}

function showError(msg) {
  el.errorBanner.textContent = msg;
  el.errorBanner.classList.remove("hidden");
}

function clearError() {
  el.errorBanner.textContent = "";
  el.errorBanner.classList.add("hidden");
}

let toastTimer = null;
function showToast(message) {
  if (!el.toast) return;
  el.toast.textContent = message;
  el.toast.classList.remove("hidden");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.toast.classList.add("hidden");
  }, 1800);
}

function setGenerating(flag) {
  state.generating = flag;
  el.spinner.classList.toggle("hidden", !flag);
  el.sendBtn.disabled = flag;
}

function pushMessage(role, text, meta = {}) {
  const s = currentSession();
  if (!s) return;
  s.messages.push({ role, text, ts: new Date().toISOString(), ...meta });
  saveState();
}

function updateLastAssistantMessage(patch) {
  const s = currentSession();
  if (!s || s.messages.length === 0) return;
  const last = s.messages[s.messages.length - 1];
  if (last.role === "assistant") {
    Object.assign(last, patch);
  }
  saveState();
}

function renderSessions() {
  el.sessionsList.innerHTML = "";
  Object.values(state.sessions).forEach((s) => {
    const div = document.createElement("div");
    div.className = `session-item ${s.id === state.currentSessionId ? "active" : ""}`;
    div.innerHTML = `<span class="session-name">${escapeHtml(s.name)}</span><div class="session-actions"><button class="btn small" data-reset="${s.id}">Reset</button><button class="btn small danger" data-delete="${s.id}">Delete</button></div>`;
    div.addEventListener("click", (ev) => {
      if (ev.target.dataset.reset || ev.target.dataset.delete) return;
      switchSession(s.id);
    });

    const resetBtn = div.querySelector("button[data-reset]");
    resetBtn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      await fetch(`/memory/reset?session_id=${encodeURIComponent(s.id)}`, { method: "POST" });
      s.messages = [];
      saveState();
      renderMessages();
    });

    const deleteBtn = div.querySelector("button[data-delete]");
    deleteBtn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      await deleteSession(s.id);
    });

    el.sessionsList.appendChild(div);
  });
}

function parseSectionsFromText(text) {
  // Phase 8/9 UI formatter: normalize backend response sections for clean rendering.
  const sections = {};
  const re =
    /(?:\*\*)?(Summary|Likely Cause|Evidence|Next 3 Actions|Escalate If|Confidence|What points to this|What to do now|Escalate when)(?:\*\*)?:\s*/gi;

  const matches = [...text.matchAll(re)];
  if (matches.length === 0) return sections;

  for (let i = 0; i < matches.length; i++) {
    const name = matches[i][1];
    const start = matches[i].index + matches[i][0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index : text.length;
    const normalized =
      name.toLowerCase() === "what points to this"
        ? "Evidence"
        : name.toLowerCase() === "what to do now"
          ? "Next 3 Actions"
          : name.toLowerCase() === "escalate when"
            ? "Escalate If"
            : name;
    sections[normalized] = text.slice(start, end).trim();
  }
  return sections;
}

function feedbackControls(message, index) {
  // Phase 7: Feedback controls shown only after assistant completion.
  if (message.role !== "assistant") return "";
  if (!message.query || !message.complete) return "";

  const voted = message.feedbackVote || "";
  return `
    <div class="feedback">
      <span class="feedback-label">Helpful?</span>
      <button class="icon-btn ${voted === "up" ? "active" : ""}" data-feedback="${index}" data-vote="up" title="Thumbs up">&#128077;</button>
      <button class="icon-btn ${voted === "down" ? "active" : ""}" data-feedback="${index}" data-vote="down" title="Thumbs down">&#128078;</button>
    </div>
  `;
}

function qualityBadges(message) {
  const q = message.quality || {};
  if (Object.keys(q).length === 0) return "";
  return `
    <div class="quality-badges">
      <span class="badge">Specificity ${q.specificity_score ?? "n/a"}</span>
      <span class="badge">Citation ${q.evidence_citation_rate ?? "n/a"}</span>
      <span class="badge">Actions ${q.actionable_step_count ?? "n/a"}</span>
      <span class="badge">Safety ${q.safety_pass ? "pass" : "fail"}</span>
    </div>
  `;
}

function normalizeTextBlock(text) {
  return String(text)
    .replaceAll("**", "")
    .replace(/^\s*[-*]\s*/gm, "- ")
    .trim();
}

function sectionBlock(title, content, cls = "") {
  if (!content) return "";
  return `
    <section class="${cls}">
      <h4>${title}</h4>
      <div>${formatSectionContent(content)}</div>
    </section>
  `;
}

function formatSectionContent(text) {
  const normalized = normalizeTextBlock(text);
  const lines = normalized.split("\n").filter((x) => x.trim().length > 0);
  const hasBullets = lines.some((ln) => ln.trim().startsWith("- ") || /^\d+\.\s+/.test(ln.trim()));
  if (!hasBullets) {
    return `<pre>${escapeHtml(normalized)}</pre>`;
  }

  const items = lines
    .map((ln) => ln.trim())
    .filter((ln) => ln.startsWith("- ") || /^\d+\.\s+/.test(ln))
    .map((ln) => {
      const cleaned = ln.startsWith("- ") ? ln.slice(2) : ln.replace(/^\d+\.\s+/, "");
      return `<li>${escapeHtml(cleaned)}</li>`;
    })
    .join("");
  return `<ul>${items}</ul>`;
}

function renderAssistantMessage(message) {
  const raw = message.text || "";
  const sections = message.sections || parseSectionsFromText(raw);

  const hasSchema = REQUIRED_SECTIONS.some((s) => sections[s]);
  if (!hasSchema) {
    return `<div class="assistant-flow"><pre>${escapeHtml(normalizeTextBlock(raw))}</pre></div>${qualityBadges(message)}`;
  }

  return `
    ${qualityBadges(message)}
    <article class="assistant-flow">
      ${sectionBlock("Summary", sections["Summary"])}
      ${sectionBlock("Likely Cause", sections["Likely Cause"])}
      <div class="block-highlight">${sectionBlock("Next 3 Actions", sections["Next 3 Actions"])}</div>
      <div class="block-escalate">${sectionBlock("Escalate If", sections["Escalate If"])}</div>
      ${sectionBlock("Confidence", sections["Confidence"])}
      <details style="margin-top:8px;">
        <summary>Evidence</summary>
        <div style="margin-top:6px;">${formatSectionContent(sections["Evidence"] || "")}</div>
      </details>
      <details style="margin-top:8px;">
        <summary>Raw details</summary>
        <pre>${escapeHtml(normalizeTextBlock(raw))}</pre>
      </details>
    </article>
  `;
}

function renderMessages() {
  const s = currentSession();
  el.messages.innerHTML = "";
  if (!s) return;

  s.messages.forEach((m, index) => {
    const wrapper = document.createElement("div");
    wrapper.className = `msg ${m.role}`;
    wrapper.innerHTML = m.role === "assistant"
      ? `${renderAssistantMessage(m)}${feedbackControls(m, index)}`
      : `<div>${escapeHtml(m.text || "")}</div>`;
    el.messages.appendChild(wrapper);
  });

  Array.from(el.messages.querySelectorAll("button[data-feedback]")).forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = Number(btn.dataset.feedback);
      const vote = btn.dataset.vote;
      await submitFeedback(idx, vote);
    });
  });

  el.messages.scrollTop = el.messages.scrollHeight;
}

function escapeHtml(raw) {
  return String(raw)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function submitFeedback(msgIndex, vote) {
  // Phase 7: Thumbs up/down mapped to persisted rating signal.
  const s = currentSession();
  if (!s) return;
  const msg = s.messages[msgIndex];
  if (!msg || !msg.query) return;

  const rating = vote === "up" ? 5 : 1;
  const notes = vote === "up" ? "thumbs_up" : "thumbs_down";

  try {
    const params = new URLSearchParams({
      q: msg.query,
      rating: String(rating),
      session_id: s.id,
      notes,
    });
    const res = await fetch(`/feedback?${params.toString()}`, { method: "POST" });
    if (!res.ok) throw new Error("Feedback request failed.");
    msg.feedbackVote = vote;
    saveState();
    renderMessages();
  } catch (err) {
    showError(`Feedback failed: ${err.message}`);
  }
}

async function sendMessage() {
  // Phase 6/8: Core chat loop with session context + robust UX states.
  if (state.generating) return;
  const query = el.queryInput.value.trim();
  if (!query) return;
  clearError();

  const { mode, strategy, retrieval, tools, stream, responseStyle } = ASSISTANT_DEFAULTS;
  const sessionId = state.currentSessionId;

  state.lastRequest = { query, mode, strategy, retrieval, tools, stream, sessionId, responseStyle };

  pushMessage("user", query);
  pushMessage("assistant", "", { query, sections: {}, quality: {}, complete: false });
  renderMessages();
  el.queryInput.value = "";
  setGenerating(true);

  try {
    if (mode === "baseline") {
      const res = await fetch(`/baseline?q=${encodeURIComponent(query)}`);
      if (!res.ok) throw new Error("Baseline call failed.");
      const data = await res.json();
      updateLastAssistantMessage({ text: data.response || "No response", sections: {}, quality: {}, complete: true });
      renderMessages();
      return;
    }

    if (stream) {
      await runStreamQuery({ query, strategy, retrieval, tools, sessionId, responseStyle });
    } else {
      const params = new URLSearchParams({
        q: query,
        strategy,
        retrieval: String(retrieval),
        tools: String(tools),
        session_id: sessionId,
        response_style: responseStyle,
      });
      const res = await fetch(`/query?${params.toString()}`);
      if (!res.ok) throw new Error("Query failed.");
      const data = await res.json();
      updateLastAssistantMessage({
        text: data.response || "No response",
        sections: data.sections || parseSectionsFromText(data.response || ""),
        quality: data.quality || {},
        complete: true,
      });
      renderMessages();
    }
  } catch (err) {
    updateLastAssistantMessage({
      text: "Request failed. Use Retry Last or check backend logs.",
      sections: {},
      quality: {},
      complete: true,
    });
    renderMessages();
    showError(err.message || "Unknown error.");
  } finally {
    setGenerating(false);
  }
}

async function runStreamQuery({ query, strategy, retrieval, tools, sessionId, responseStyle }) {
  // Phase 8: Streaming response rendering for interactive perceived latency.
  return new Promise((resolve, reject) => {
    let text = "";
    let sections = {};
    let quality = {};

    const params = new URLSearchParams({
      q: query,
      strategy,
      retrieval: String(retrieval),
      tools: String(tools),
      session_id: sessionId,
      response_style: responseStyle,
    });

    const es = new EventSource(`/query_stream?${params.toString()}`);

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.done) {
          updateLastAssistantMessage({
            text,
            sections: sections || parseSectionsFromText(text),
            quality,
            complete: true,
          });
          renderMessages();
          es.close();
          resolve();
          return;
        }
        if (payload.chunk) {
          text += payload.chunk;
          updateLastAssistantMessage({ text, sections: parseSectionsFromText(text), quality, complete: false });
          renderMessages();
        }
        if (payload.sections) sections = payload.sections;
        if (payload.quality) quality = payload.quality;
      } catch {
        es.close();
        reject(new Error("Invalid stream payload."));
      }
    };

    es.onerror = () => {
      es.close();
      reject(new Error("Streaming connection error."));
    };
  });
}

function setTab(tab) {
  const chat = tab === "chat";
  el.chatTabBtn.classList.toggle("active", chat);
  el.evalTabBtn.classList.toggle("active", !chat);
  el.chatTab.classList.toggle("hidden", !chat);
  el.evalTab.classList.toggle("hidden", chat);
}

async function runEvaluation() {
  // Phase 9: Trigger evaluation harness from UI.
  clearError();
  el.evalSpinner.classList.remove("hidden");
  el.runEvalBtn.disabled = true;
  el.evalOutput.innerHTML = "";

  try {
    const res = await fetch("/evaluate");
    if (!res.ok) throw new Error("/evaluate failed");
    const data = await res.json();
    renderEvaluation(data);
  } catch (err) {
    showError(err.message || "Evaluation failed.");
  } finally {
    el.evalSpinner.classList.add("hidden");
    el.runEvalBtn.disabled = false;
  }
}

function renderEvaluation(data) {
  const rows = (data.baseline_vs_advanced || [])
    .map(
      (r) => `
      <tr>
        <td>${escapeHtml(r.query || "")}</td>
        <td><details><summary>View</summary>${escapeHtml(r.baseline || "")}</details></td>
        <td><details><summary>View</summary>${escapeHtml(r.advanced || "")}</details></td>
        <td>${r.baseline_keyword_hits ?? ""}</td>
        <td>${r.advanced_keyword_hits ?? ""}</td>
        <td>${r.advanced_metrics?.specificity_score ?? ""}</td>
        <td>${r.advanced_metrics?.evidence_citation_rate ?? ""}</td>
        <td>${r.advanced_metrics?.actionable_step_count ?? ""}</td>
        <td>${r.advanced_metrics?.safety_pass ? "pass" : "fail"}</td>
      </tr>`
    )
    .join("");

  const promptCards = Object.entries(data.prompt_comparison || {})
    .map(([k, v]) => `<h4>${k}</h4><details><summary>Output</summary><pre>${escapeHtml(String(v))}</pre></details>`)
    .join("");

  const summary = data.metrics_summary || {};
  const summaryHtml = `
    <div class="quality-badges">
      <span class="badge">Avg Specificity ${summary.specificity_score ?? "n/a"}</span>
      <span class="badge">Avg Citation ${summary.evidence_citation_rate ?? "n/a"}</span>
      <span class="badge">Avg Actions ${summary.actionable_step_count ?? "n/a"}</span>
      <span class="badge">Safety Pass Rate ${summary.safety_pass_rate ?? "n/a"}</span>
    </div>
  `;

  el.evalOutput.innerHTML = `
    <h3>Evaluation Metrics</h3>
    ${summaryHtml}
    <h3>Baseline vs Advanced</h3>
    <table>
      <thead>
        <tr>
          <th>Query</th>
          <th>Baseline</th>
          <th>Advanced</th>
          <th>Baseline Hits</th>
          <th>Advanced Hits</th>
          <th>Specificity</th>
          <th>Citation Rate</th>
          <th>Action Count</th>
          <th>Safety</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <h3>Prompt Comparison</h3>
    ${promptCards}
  `;
}

function bindEvents() {
  el.newSessionBtn.addEventListener("click", () => {
    const name = prompt("Session name:", `Session ${Object.keys(state.sessions).length + 1}`);
    createSession(name || undefined);
    renderSessions();
    renderMessages();
  });

  el.sendBtn.addEventListener("click", sendMessage);

  el.retryBtn.addEventListener("click", async () => {
    if (!state.lastRequest || state.generating) return;
    el.queryInput.value = state.lastRequest.query;
    await sendMessage();
  });

  el.queryInput.addEventListener("keydown", (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") {
      sendMessage();
    }
  });

  el.chatTabBtn.addEventListener("click", () => setTab("chat"));
  el.evalTabBtn.addEventListener("click", () => setTab("eval"));
  el.runEvalBtn.addEventListener("click", runEvaluation);
}

function init() {
  const hasStore = loadState();
  if (!hasStore || Object.keys(state.sessions).length === 0) {
    createSession("Session 1");
  }

  if (!state.currentSessionId || !state.sessions[state.currentSessionId]) {
    state.currentSessionId = Object.keys(state.sessions)[0];
  }

  renderSessions();
  renderMessages();
  bindEvents();
}

init();
