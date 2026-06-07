const appShell = document.querySelector("#app-shell");
const form = document.querySelector("#run-form");
const requirementInput = document.querySelector("#requirement");
const runButton = document.querySelector("#run-button");
const clearButton = document.querySelector("#clear-button");
const demoRow = document.querySelector("#demo-row");
const modeSelect = document.querySelector("#mode-select");
const jobStatus = document.querySelector("#job-status");
const workflowLog = document.querySelector("#workflow-log");
const leftScroll = document.querySelector("#left-scroll");
const summaryEl = document.querySelector("#summary");
const rightPane = document.querySelector("#right-pane");
const candidatesPanel = document.querySelector("#candidates-panel");
const reportContent = document.querySelector("#report-content");
const reportToggle = document.querySelector("#report-toggle");
const builderOptions = document.querySelector("#builder-options");
const candidateModal = document.querySelector("#candidate-modal");
const candidateModalCard = document.querySelector("#candidate-modal-card");
const envButton = document.querySelector("#env-button");
const newButton = document.querySelector("#new-button");
const envPopover = document.querySelector("#env-popover");
const envGrid = document.querySelector("#env-grid");
const toast = document.querySelector("#toast");

let activeMode = "recommend";
let activePollToken = 0;
let activeJobId = null;
let renderedEventCount = 0;
let candidateEvaluations = [];
let envValues = {};
let renderedBuilderQuestionKey = null;

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const externalLink = (url) => {
  const safeUrl = escapeHtml(url || "");
  if (!safeUrl) return "暂无";
  return `<a href="${safeUrl}" target="_blank" rel="noreferrer">${safeUrl}</a>`;
};

const list = (items) => {
  if (!items || items.length === 0) return "<p>暂无</p>";
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
};

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.hidden = true;
  }, 4600);
}

function setMode(mode) {
  activeMode = mode;
  modeSelect.value = mode;
}

modeSelect.addEventListener("change", () => {
  setMode(modeSelect.value);
});

async function loadDemoCases() {
  try {
    const response = await fetch("/api/demo-cases");
    const payload = await response.json();
    const cases = payload.cases || {};
    demoRow.innerHTML = Object.entries(cases)
      .map(([name, requirement]) => {
        return `<button class="demo-button" type="button" data-requirement="${escapeHtml(
          requirement,
        )}" data-mode="${name === "build" ? "build" : "recommend"}">Demo / ${escapeHtml(name)}</button>`;
      })
      .join("");
  } catch (error) {
    showToast(`无法读取演示案例：${error.message}`);
  }
}

demoRow.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-requirement]");
  if (!button) return;
  requirementInput.value = button.dataset.requirement;
  setMode(button.dataset.mode);
  requirementInput.focus();
});

clearButton.addEventListener("click", () => {
  requirementInput.value = "";
  requirementInput.focus();
});

newButton.addEventListener("click", async () => {
  const confirmed = window.confirm("确认开始新的会话？当前运行会被取消，页面状态和本地中间变量会被清空。");
  if (!confirmed) return;
  activePollToken += 1;
  if (activeJobId) {
    try {
      await fetch(`/api/runs/${activeJobId}/cancel`, { method: "POST" });
    } catch (error) {
      showToast(`取消运行失败：${error.message}`);
    }
  }
  requirementInput.value = "";
  requirementInput.disabled = false;
  resetRunState();
  jobStatus.textContent = "Idle";
  clearButton.disabled = false;
  runButton.disabled = false;
  runButton.textContent = "Run";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const requirement = requirementInput.value.trim();
  if (!requirement) {
    showToast("请输入需求。");
    return;
  }

  resetRunState();
  requirementInput.disabled = true;
  clearButton.disabled = true;
  runButton.disabled = true;
  runButton.textContent = "Running";
  jobStatus.textContent = "Starting";

  activePollToken += 1;
  const pollToken = activePollToken;

  try {
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ requirement, mode: activeMode }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "运行失败");
    activeJobId = payload.job_id;
    renderJob(payload);
    await pollJob(payload.job_id, pollToken);
  } catch (error) {
    showToast(error.message);
    jobStatus.textContent = "Failed";
  } finally {
    requirementInput.disabled = false;
    clearButton.disabled = false;
    runButton.disabled = false;
    runButton.textContent = "Run";
  }
});

function resetRunState() {
  renderedEventCount = 0;
  activeJobId = null;
  candidateEvaluations = [];
  workflowLog.innerHTML = "";
  summaryEl.innerHTML = "";
  candidatesPanel.innerHTML = "";
  reportContent.innerHTML = "";
  builderOptions.hidden = true;
  builderOptions.innerHTML = "";
  renderedBuilderQuestionKey = null;
  rightPane.classList.remove("report-expanded");
  appShell.classList.remove("has-results");
  rightPane.setAttribute("aria-hidden", "true");
  reportToggle.textContent = "⛶";
  reportToggle.setAttribute("aria-label", "放大报告");
}

async function pollJob(jobId, pollToken) {
  while (pollToken === activePollToken) {
    await delay(1000);
    const response = await fetch(`/api/runs/${jobId}`);
    const snapshot = await response.json();
    if (!response.ok) throw new Error(snapshot.error || "无法读取运行状态");
    renderJob(snapshot);
    if (snapshot.status === "complete") {
      renderPayload(snapshot.result);
      return;
    }
    if (snapshot.status === "failed") {
      throw new Error(snapshot.error || "运行失败");
    }
    if (snapshot.status === "cancelled") {
      return;
    }
  }
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function renderJob(job) {
  jobStatus.textContent = job.status || "Unknown";
  renderWorkflow(job.events || [], job.status);
  renderBuilderQuestion(job);
}

function renderWorkflow(events, jobState) {
  const wasNearBottom =
    leftScroll.scrollHeight - leftScroll.scrollTop - leftScroll.clientHeight < 24;
  const newEvents = events.slice(renderedEventCount);
  newEvents.forEach((event, offset) => {
    const index = renderedEventCount + offset;
    const isCurrent = index === events.length - 1 && jobState === "running";
    workflowLog.insertAdjacentHTML("beforeend", workflowEventHtml(event, isCurrent));
  });
  renderedEventCount = events.length;
  if (wasNearBottom && newEvents.length > 0) {
    leftScroll.scrollTop = leftScroll.scrollHeight;
  }
}

function workflowEventHtml(event, isCurrent) {
  const stateClass = event.status === "failed" ? "is-failed" : isCurrent ? "is-running" : "";
  return `
    <article class="workflow-event ${stateClass}">
      <div class="workflow-event-title">
        <span>${escapeHtml(event.agent)} / ${escapeHtml(event.skill)}</span>
        <span class="pill">${escapeHtml(event.status)}</span>
      </div>
      <div class="workflow-event-summary">${escapeHtml(event.summary || "已记录事件。")}</div>
      ${renderWorkflowDetails(event.metadata || {})}
    </article>
  `;
}

function renderWorkflowDetails(metadata) {
  const details = [];
  if (metadata.capabilities?.length) details.push(`capabilities: ${metadata.capabilities.join(", ")}`);
  if (metadata.sources?.length) {
    metadata.sources.slice(0, 6).forEach((source) => {
      details.push(
        typeof source === "string"
          ? `source: ${source}`
          : `source: ${source.source_id || source.name} · ${source.entrypoint || source.name || ""}`,
      );
    });
  }
  if (metadata.queries?.length) {
    metadata.queries.slice(0, 8).forEach((query) => {
      details.push(typeof query === "string" ? `query: ${query}` : `query @ ${query.source_id || "source"}: ${query.text}`);
    });
  }
  if (metadata.results?.length) {
    metadata.results.slice(0, 8).forEach((result) => {
      details.push(`result [${result.status}] ${result.title || result.source_id || ""} ${result.url || ""}`);
    });
  }
  if (metadata.targets?.length) {
    metadata.targets.slice(0, 8).forEach((target) => {
      details.push(`read target: ${target.title || ""} ${target.url || ""}`);
    });
  }
  if (metadata.contents?.length) {
    metadata.contents.slice(0, 8).forEach((content) => {
      details.push(`content [${content.status}] ${content.title || ""} ${content.url || ""}`);
    });
  }
  if (metadata.statuses?.length) details.push(`statuses: ${metadata.statuses.join(", ")}`);
  if (metadata.reason) details.push(`reason: ${metadata.reason}`);
  if (!details.length) return "";
  return `<div class="workflow-details">${details
    .map((detail) => `<div class="workflow-detail">${escapeHtml(detail)}</div>`)
    .join("")}</div>`;
}

function renderPayload(payload) {
  renderSummary(payload.summary);
  candidateEvaluations = payload.result.evaluations || [];
  renderCandidates(candidateEvaluations);
  reportContent.innerHTML = renderMarkdown(payload.report_markdown || "SkillPilot运行报告");
  appShell.classList.add("has-results");
  rightPane.setAttribute("aria-hidden", "false");
  showToast("运行完成。");
}

function renderSummary(summary) {
  const wasNearBottom =
    leftScroll.scrollHeight - leftScroll.scrollTop - leftScroll.clientHeight < 24;
  summaryEl.innerHTML = `
    <article class="summary-card">
      <div class="score-row">
        <span class="pill">${escapeHtml(summary.decision_type)}</span>
        <span class="pill">type: ${escapeHtml(summary.recommended_type)}</span>
        <span class="pill risk-${escapeHtml(summary.top_risk || "low")}">risk: ${escapeHtml(summary.top_risk || "n/a")}</span>
      </div>
      <p>${escapeHtml(summary.decision_reason)}</p>
      <div class="metric-grid">
        <div class="metric"><span>Top</span><strong>${escapeHtml(summary.top_candidate || "none")}</strong></div>
        <div class="metric"><span>Score</span><strong>${escapeHtml(summary.top_score ?? "n/a")}</strong></div>
        <div class="metric"><span>Candidates</span><strong>${escapeHtml(summary.candidate_count)}</strong></div>
        <div class="metric"><span>Reads</span><strong>${escapeHtml(`${summary.successful_reads}/${summary.read_count}`)}</strong></div>
        <div class="metric"><span>Events</span><strong>${escapeHtml(summary.trace_event_count)}</strong></div>
        <div class="metric"><span>Draft</span><strong>${escapeHtml(summary.skill_draft_name || "none")}</strong></div>
      </div>
    </article>
  `;
  if (wasNearBottom) {
    leftScroll.scrollTop = leftScroll.scrollHeight;
  }
}

function renderCandidates(evaluations) {
  if (!evaluations.length) {
    candidatesPanel.innerHTML = '<div class="empty-state">No candidates</div>';
    return;
  }
  candidatesPanel.innerHTML = evaluations
    .map((evaluation, index) => {
      const candidate = evaluation.candidate;
      return `
        <button class="candidate-card" type="button" data-index="${index}">
          <span class="candidate-name">${escapeHtml(candidate.name)}</span>
          <span class="candidate-score">${escapeHtml(evaluation.match_score)}</span>
          <span class="pill risk-${escapeHtml(evaluation.risk_level)}">${escapeHtml(evaluation.risk_level)}</span>
        </button>
      `;
    })
    .join("");
}

candidatesPanel.addEventListener("click", (event) => {
  const card = event.target.closest(".candidate-card");
  if (!card) return;
  openCandidateModal(candidateEvaluations[Number(card.dataset.index)]);
});

function openCandidateModal(evaluation) {
  if (!evaluation) return;
  const candidate = evaluation.candidate;
  candidateModalCard.innerHTML = `
    <button class="icon-button modal-close" type="button" data-close-modal aria-label="关闭">×</button>
    <h2>${escapeHtml(candidate.name)}</h2>
    <div class="score-row">
      <span class="pill">score ${escapeHtml(evaluation.match_score)}</span>
      <span class="pill">type ${escapeHtml(candidate.extension_type)}</span>
      <span class="pill risk-${escapeHtml(evaluation.risk_level)}">${escapeHtml(evaluation.risk_level)}</span>
    </div>
    <p>${escapeHtml(candidate.description)}</p>
    <p><strong>source</strong><br>${externalLink(candidate.source_url)}</p>
    <p><strong>matched</strong></p>
    ${list(evaluation.matched_capabilities)}
    <p><strong>missing</strong></p>
    ${list(evaluation.missing_capabilities)}
    <p><strong>risk</strong></p>
    ${list(evaluation.risk_reasons)}
    <p><strong>reason</strong><br>${escapeHtml(evaluation.reason)}</p>
  `;
  candidateModal.hidden = false;
}

candidateModal.addEventListener("click", (event) => {
  if (event.target.closest("[data-close-modal]")) {
    candidateModal.hidden = true;
  }
});

reportToggle.addEventListener("click", () => {
  const expanded = rightPane.classList.toggle("report-expanded");
  reportToggle.textContent = expanded ? "⤢" : "⛶";
  reportToggle.setAttribute("aria-label", expanded ? "缩小报告" : "放大报告");
});

function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let inCode = false;
  let listOpen = false;
  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (line.startsWith("```")) {
      if (inCode) {
        html.push("</code></pre>");
        inCode = false;
      } else {
        closeList();
        html.push("<pre><code>");
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      html.push(`${escapeHtml(rawLine)}\n`);
      continue;
    }
    if (!line.trim()) {
      closeList();
      continue;
    }
    if (line.startsWith("### ")) {
      closeList();
      html.push(`<h3>${inlineMarkdown(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      closeList();
      html.push(`<h2>${inlineMarkdown(line.slice(3))}</h2>`);
    } else if (line.startsWith("# ")) {
      closeList();
      html.push(`<h1>${inlineMarkdown(line.slice(2))}</h1>`);
    } else if (/^\s*[-*]\s+/.test(rawLine)) {
      if (!listOpen) {
        html.push("<ul>");
        listOpen = true;
      }
      html.push(`<li>${inlineMarkdown(line.replace(/^\s*[-*]\s+/, ""))}</li>`);
    } else {
      closeList();
      html.push(`<p>${inlineMarkdown(line)}</p>`);
    }
  }
  closeList();
  if (inCode) html.push("</code></pre>");
  return html.join("");

  function closeList() {
    if (listOpen) {
      html.push("</ul>");
      listOpen = false;
    }
  }
}

function inlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

function renderBuilderQuestion(job) {
  const question = job.pending_question;
  if (!question || job.status !== "waiting_for_builder_answer") {
    builderOptions.hidden = true;
    builderOptions.innerHTML = "";
    renderedBuilderQuestionKey = null;
    return;
  }
  const questionKey = `${question.question_id}:${question.prompt}`;
  if (!builderOptions.hidden && renderedBuilderQuestionKey === questionKey) {
    return;
  }
  renderedBuilderQuestionKey = questionKey;
  builderOptions.hidden = false;
  builderOptions.innerHTML = `
    <div class="builder-question">
      <strong>${escapeHtml(question.prompt)}</strong>
      <p>${escapeHtml(question.reason || "")}</p>
      <div class="builder-option-row">
        ${(question.options || [])
          .map(
            (option) => `
              <button class="builder-option" type="button" data-question-id="${escapeHtml(
                question.question_id,
              )}" data-answer="${escapeHtml(option.option_id)}">
                ${escapeHtml(option.label)}
              </button>
            `,
          )
          .join("")}
      </div>
      <div class="builder-free-text">
        <input type="text" class="builder-answer-input" data-question-id="${escapeHtml(
          question.question_id,
        )}" placeholder="自定义回答...">
        <button class="builder-submit" type="button" data-question-id="${escapeHtml(
          question.question_id,
        )}">Submit</button>
      </div>
    </div>
  `;
}

builderOptions.addEventListener("click", async (event) => {
  const button = event.target.closest(".builder-option");
  const submit = event.target.closest(".builder-submit");
  if (!activeJobId || (!button && !submit)) return;
  const questionId = button?.dataset.questionId || submit?.dataset.questionId;
  const answer =
    button?.dataset.answer ||
    builderOptions.querySelector(`.builder-answer-input[data-question-id="${CSS.escape(questionId)}"]`)?.value ||
    "";
  try {
    const response = await fetch(`/api/runs/${activeJobId}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question_id: questionId,
        answer,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "提交回答失败");
    renderJob(payload);
  } catch (error) {
    showToast(error.message);
  }
});

envButton.addEventListener("click", async () => {
  const willOpen = envPopover.hidden;
  envPopover.hidden = !willOpen;
  envButton.setAttribute("aria-expanded", String(willOpen));
  if (willOpen) await loadEnv();
});

async function loadEnv() {
  try {
    const response = await fetch("/api/env");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "无法读取环境变量");
    envValues = Object.fromEntries((payload.variables || []).map((item) => [item.name, item.value || ""]));
    envGrid.innerHTML = (payload.variables || [])
      .map((item) => {
        const inputType = item.sensitive ? "password" : "text";
        const masked = item.sensitive && item.masked ? "true" : "false";
        return `
          <div class="env-row">
            <label for="env-${escapeHtml(item.name)}">${escapeHtml(item.name)}</label>
            <input id="env-${escapeHtml(item.name)}" type="${inputType}" data-env-name="${escapeHtml(
              item.name,
            )}" data-sensitive="${item.sensitive ? "true" : "false"}" data-masked="${masked}" data-masked-value="${escapeHtml(
              item.value || "",
            )}" value="${escapeHtml(
              item.value || "",
            )}">
            <button class="env-apply" type="button" data-env-target="${escapeHtml(item.name)}">✓</button>
          </div>
        `;
      })
      .join("");
  } catch (error) {
    showToast(error.message);
  }
}

envGrid.addEventListener("focusin", (event) => {
  const input = event.target.closest("input[data-env-name]");
  if (!input || input.dataset.sensitive !== "true" || input.dataset.masked !== "true") return;
  window.setTimeout(() => input.select(), 0);
});

envGrid.addEventListener("input", (event) => {
  const input = event.target.closest("input[data-env-name]");
  if (!input || input.dataset.sensitive !== "true") return;
  if (input.value !== input.dataset.maskedValue) {
    input.dataset.masked = "false";
  }
});

envGrid.addEventListener("click", async (event) => {
  const button = event.target.closest(".env-apply");
  if (!button) return;
  const name = button.dataset.envTarget;
  const input = envGrid.querySelector(`input[data-env-name="${CSS.escape(name)}"]`);
  if (!input) return;
  if (input.dataset.sensitive === "true" && input.dataset.masked === "true") {
    showToast(`${name} 未修改。`);
    return;
  }
  try {
    const response = await fetch("/api/env", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ updates: { [name]: input.value } }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "保存失败");
    envValues = Object.fromEntries((payload.variables || []).map((item) => [item.name, item.value || ""]));
    showToast(`${name} 已更新。`);
    const updated = (payload.variables || []).find((item) => item.name === name);
    if (updated?.sensitive) {
      input.value = updated.value || "";
      input.dataset.maskedValue = updated.value || "";
      input.dataset.masked = updated.masked ? "true" : "false";
    }
  } catch (error) {
    showToast(error.message);
  }
});

loadDemoCases();
