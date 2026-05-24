const title = document.querySelector("#debate-title");
const verdict = document.querySelector("#verdict-text");
const messages = document.querySelector("#messages");
const count = document.querySelector("#message-count");
const form = document.querySelector("#debate-form");
const button = document.querySelector("#run-button");
const tokenDetails = document.querySelector("#token-details");
const tokenStats = document.querySelector("#token-stats");

function labelFor(name) {
  return name === "Debater_B" ? "Debater B" : "Debater A";
}

function renderTokenStats(stats) {
  if (!stats) { tokenDetails.hidden = true; return; }
  const tIn  = (stats.total_tokens_in  || 0).toLocaleString();
  const tOut = (stats.total_tokens_out || 0).toLocaleString();
  const tTot = ((stats.total_tokens_in || 0) + (stats.total_tokens_out || 0)).toLocaleString();
  const cost = (stats.estimated_cost_usd || 0).toFixed(6);
  tokenStats.innerHTML = `
    <dt>Tokens in</dt>  <dd>${tIn}</dd>
    <dt>Tokens out</dt> <dd>${tOut}</dd>
    <dt>Total</dt>      <dd>${tTot}</dd>
    <dt>Est. cost</dt>  <dd>$${cost} USD</dd>
  `;
  tokenDetails.hidden = false;
}

function render(data) {
  const history = data.history || [];
  title.textContent = data.topic || "AI Debate Platform";
  verdict.textContent = data.verdict || "Run a debate to generate the judge verdict.";
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
      <h3>${labelFor(name)} - Turn ${index + 1}</h3>
      <p></p>
    `;
    card.querySelector("p").textContent = item.content || "";
    messages.appendChild(card);
  });
}

function resetLive(topicText) {
  title.textContent = topicText || "AI Debate Platform";
  verdict.textContent = "Waiting for the debate to finish before judging...";
  count.textContent = "0 messages";
  messages.innerHTML = "";
}

function appendMessage(item, index) {
  const name = item.name || item.role || "Debater";
  const card = document.createElement("article");
  card.className = `message ${name === "Debater_B" ? "b" : "a"}`;
  card.innerHTML = `
    <h3>${labelFor(name)} - Turn ${index}</h3>
    <p></p>
  `;
  card.querySelector("p").textContent = item.content || "";
  messages.appendChild(card);
  count.textContent = `${index} message${index === 1 ? "" : "s"}`;
  card.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function handleEvent(event) {
  if (event.type === "start") resetLive(event.topic);
  if (event.type === "message") appendMessage(event.message, event.count);
  if (event.type === "judging") verdict.textContent = "The judge is analyzing the full debate...";
  if (event.type === "verdict") render(event);
  if (event.type === "error") throw new Error(event.error || "Debate failed.");
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

async function loadLatest() {
  const response = await fetch("/api/results");
  render(await response.json());
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

loadLatest();
