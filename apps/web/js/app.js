const state = {
  socket: null,
  sessionId: null,
};

const $ = (selector) => document.querySelector(selector);

function setConnection(status, label) {
  const pill = $("#connectionState");
  pill.className = `status-pill ${status}`;
  $("#connectionText").textContent = label;
}

function addEvent(event) {
  const container = $("#events");
  container.querySelector(".empty-state")?.remove();

  const row = document.createElement("div");
  row.className = "event-row animate-in";
  row.innerHTML = `
    <div class="flex items-center justify-between gap-3">
      <span class="text-[11px] font-bold text-slate-300">${escapeHtml(event.type)}</span>
      <span class="font-mono text-[10px] text-slate-600">${new Date(event.timestamp).toLocaleTimeString()}</span>
    </div>
    <p class="mt-1 truncate text-[10px] text-slate-500">${escapeHtml(event.id)}</p>
  `;
  container.prepend(row);
}

function renderTranscript(event) {
  const text = event.payload?.text;
  if (!text) return;

  const container = $("#transcript");
  container.querySelector(".empty-state")?.remove();

  const item = document.createElement("div");
  item.className = `transcript-item ${event.type.endsWith(".final") ? "final" : ""} animate-in`;
  item.innerHTML = `
    <p class="text-[10px] font-bold uppercase tracking-wider text-slate-600">${event.type === "transcript.final" ? "Final" : "Live"}</p>
    <p class="mt-1 text-sm leading-6 text-slate-300">${escapeHtml(text)}</p>
  `;
  container.prepend(item);
}

function renderSuggestion(event) {
  if (!event.type.startsWith("media.suggestion")) return;
  const container = $("#suggestions");
  container.querySelector(".empty-state")?.remove();

  const payload = event.payload || {};
  const card = document.createElement("div");
  card.className = "rounded-2xl border border-blue-400/10 bg-blue-400/5 p-4 animate-in";
  card.innerHTML = `
    <div class="flex items-start gap-3">
      <div class="icon-box"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
      <div class="min-w-0 flex-1">
        <p class="text-sm font-bold text-slate-200">${escapeHtml(payload.title || "Media suggestion")}</p>
        <p class="mt-1 text-xs leading-5 text-slate-400">${escapeHtml(payload.description || "Review this suggestion before publishing.")}</p>
        <div class="mt-3 flex gap-2">
          <button class="approve-btn rounded-lg bg-white px-3 py-1.5 text-[10px] font-extrabold text-black hover:bg-slate-200">APPROVE</button>
          <button class="rounded-lg border border-white/10 px-3 py-1.5 text-[10px] font-extrabold text-slate-300 hover:bg-white/5">IGNORE</button>
        </div>
      </div>
    </div>
  `;
  container.prepend(card);
}

function handleEvent(event) {
  addEvent(event);
  if (event.type.startsWith("transcript.")) renderTranscript(event);
  renderSuggestion(event);
}

function connect() {
  if (!state.sessionId) return;

  state.socket?.close();
  setConnection("connecting", "CONNECTING");

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socketUrl = `${protocol}://${location.host}/ws/sessions/${state.sessionId}`;
  state.socket = new WebSocket(socketUrl);

  state.socket.onopen = () => setConnection("online", "LIVE");
  state.socket.onclose = () => setConnection("offline", "OFFLINE");
  state.socket.onerror = () => setConnection("offline", "ERROR");
  state.socket.onmessage = (message) => {
    try { handleEvent(JSON.parse(message.data)); }
    catch (error) { console.error("Invalid realtime event", error); }
  };
}

function startSession() {
  state.sessionId = crypto.randomUUID();
  $("#sessionId").textContent = state.sessionId;
  $("#sessionButton").innerHTML = '<i class="fa-solid fa-rotate mr-2"></i>Restart Session';
  connect();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
  }[char]));
}

$("#sessionButton").addEventListener("click", startSession);


/**
 * Puter AI adapter.
 * Great Church AI does not store provider API keys in the browser.
 * Puter.js exposes AI services through the user's Puter session/user-pays model.
 */
const puterAI = {
  available: () => typeof window.puter !== "undefined" && typeof window.puter.ai?.chat === "function",

  async analyzeContext(transcript, context = {}) {
    if (!this.available() || !transcript?.trim()) return null;

    const prompt = [
      "You are the church-intelligence layer for Great Church AI.",
      "Analyze the following church-service transcript.",
      "Return ONLY valid JSON with keys: title, description, category, confidence.",
      "Do not recommend actions that bypass the human operator.",
      "Identify useful media opportunities such as Scripture, sermon topic, worship moment, announcement, prayer, or teaching.",
      "",
      "Transcript:",
      transcript,
      "",
      "Recent context:",
      JSON.stringify(context)
    ].join("\n");

    try {
      const response = await window.puter.ai.chat(prompt, {
        model: "gpt-5-nano"
      });

      const raw = typeof response === "string"
        ? response
        : response?.message?.content || response?.text || "";

      const cleaned = String(raw).replace(/^\`\`\`json\s*/i, "").replace(/\s*\`\`\`$/, "");
      return JSON.parse(cleaned);
    } catch (error) {
      console.warn("Puter AI analysis unavailable:", error);
      return null;
    }
  }
};

window.greatChurchAI = { ...(window.greatChurchAI || {}), puterAI };
