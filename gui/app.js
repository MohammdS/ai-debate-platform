const title = document.querySelector("#debate-title");
const verdict = document.querySelector("#verdict-text");
const messages = document.querySelector("#messages");
const count = document.querySelector("#message-count");
const form = document.querySelector("#debate-form");
const button = document.querySelector("#run-button");
const modelSummary = document.querySelector("#model-summary");
const judgeModel = document.querySelector("#judge-model");
const judgeNote = document.querySelector("#judge-note");
const themeToggle = document.querySelector("#theme-toggle");
const transcriptTopic = document.querySelector("#transcript-topic");
const verdictTopic = document.querySelector("#verdict-topic");
const tokenDetails = document.querySelector("#token-details");
const tokenStatsDl = document.querySelector("#token-stats");

let currentModelInfo = {};

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function cleanText(value) {
  return String(value || "")
    .replaceAll("\u00e2\u20ac\u201d", "-")
    .replaceAll("\u00e2\u20ac\u201c", "-")
    .replaceAll("\u00e2\u20ac\u02dc", "'")
    .replaceAll("\u00e2\u20ac\u2122", "'")
    .replaceAll("\u00e2\u20ac\u0153", '"')
    .replaceAll("\u00e2\u20ac\ufffd", '"')
    .replaceAll("\u00e2\u2020\u2019", "->")
    .replaceAll("\u00c2", "");
}

function renderTokenStats(stats) {
  if (!stats || typeof stats !== "object") {
    tokenDetails.hidden = true;
    return;
  }
  const rows = [
    ["Tokens in",       (stats.total_tokens_in  ?? 0).toLocaleString()],
    ["Tokens out",      (stats.total_tokens_out ?? 0).toLocaleString()],
    ["Est. cost (USD)", stats.estimated_cost_usd != null
      ? "$" + Number(stats.estimated_cost_usd).toFixed(6)
      : "–"],
  ];
  tokenStatsDl.innerHTML = rows
    .map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd>`)
    .join("");
  tokenDetails.hidden = false;
}

function labelFor(name) {
  return name === "Debater_B" ? "Debater B" : "Debater A";
}

function roleKeyFor(name) {
  return name === "Debater_B" ? "debater_b" : "debater_a";
}

function displayForRole(role) {
  const item = currentModelInfo[role] || {};
  return item.display || item.model || "Model pending";
}

function renderModelSummary(modelInfo = {}) {
  currentModelInfo = modelInfo || {};
  const roles = ["debater_a", "debater_b", "judge"];
  modelSummary.innerHTML = roles.map((role) => {
    const item = currentModelInfo[role] || {};
    const label = item.label || role;
    const display = item.display || item.model || "Model pending";
    return `<span class="model-pill">${escapeHtml(label)}: ${escapeHtml(display)}</span>`;
  }).join("");
  judgeModel.textContent = displayForRole("judge");
  judgeNote.textContent = `Judge: ${displayForRole("judge")}`;
}

function turnLabel(name, index) {
  const role = roleKeyFor(name);
  return `
    <span class="role">${escapeHtml(labelFor(name))} - Turn ${index}</span>
    <span class="model">${escapeHtml(displayForRole(role))}</span>
  `;
}

function render(data) {
  const history = data.history || [];
  const topic = cleanText(data.topic);
  renderModelSummary(data.model_info || {});
  title.textContent = "AI Debate Platform";
  transcriptTopic.textContent = topic ? `Topic: ${topic}` : "Topic will appear here after a debate starts.";
  verdictTopic.textContent = topic ? `Topic: ${topic}` : "Topic will appear here after a debate starts.";
  verdict.textContent = cleanText(data.verdict) || "Run a debate to generate the judge's verdict.";
  count.textContent = `${history.length} message${history.length === 1 ? "" : "s"}`;
  renderTokenStats(data.token_stats || null);
  messages.innerHTML = "";

  if (history.length === 0) {
    messages.innerHTML = `<p class="empty">No transcript available yet.</p>`;
    return;
  }

  history.forEach((item, index) => {
    const name = item.name || item.role || "Debater";
    const card = document.createElement("article");
    card.className = `message ${name === "Debater_B" ? "b" : "a"}`;
    card.innerHTML = `
      <h3>${turnLabel(name, index + 1)}</h3>
      <p></p>
    `;
    card.querySelector("p").textContent = cleanText(item.content);
    messages.appendChild(card);
  });
}

function resetLive(topicText, modelInfo) {
  const topic = cleanText(topicText);
  renderModelSummary(modelInfo || {});
  title.textContent = "AI Debate Platform";
  transcriptTopic.textContent = topic ? `Topic: ${topic}` : "Topic will appear here after a debate starts.";
  verdictTopic.textContent = topic ? `Topic: ${topic}` : "Topic will appear here after a debate starts.";
  verdict.textContent = "Waiting for the debate to finish before the judge scores it.";
  count.textContent = "0 messages";
  messages.innerHTML = "";
}

function appendMessage(item, index) {
  const name = item.name || item.role || "Debater";
  const card = document.createElement("article");
  card.className = `message ${name === "Debater_B" ? "b" : "a"}`;
  card.innerHTML = `
    <h3>${turnLabel(name, index)}</h3>
    <p></p>
  `;
  card.querySelector("p").textContent = cleanText(item.content);
  messages.appendChild(card);
  count.textContent = `${index} message${index === 1 ? "" : "s"}`;
  card.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function handleEvent(event) {
  if (event.type === "start") resetLive(event.topic, event.model_info);
  if (event.type === "message") appendMessage(event.message, event.count);
  if (event.type === "judging") verdict.textContent = "The judge is reviewing the full debate.";
  if (event.type === "verdict") render(event);
  if (event.type === "error") throw new Error(event.error || "Debate failed.");
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.checked = theme === "dark";
  localStorage.setItem("debate-theme", theme);
}

async function runLiveDebate(payload) {
  const response = await fetch("/api/debates/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok || !response.body) throw new Error("Debate failed to start.");

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop();
    lines.filter(Boolean).forEach((line) => handleEvent(JSON.parse(line)));
  }
}

function renderEmptyState() {
  render({
    topic: "",
    history: [],
    verdict: "",
    model_info: {}
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  button.textContent = "Debating...";
  const payload = Object.fromEntries(new FormData(form).entries());

  try {
    await runLiveDebate(payload);
  } catch (error) {
    verdict.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Run Debate";
  }
});

themeToggle.addEventListener("change", () => {
  applyTheme(themeToggle.checked ? "dark" : "light");
});

applyTheme(localStorage.getItem("debate-theme") || "light");
renderEmptyState();
