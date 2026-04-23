const STORAGE_KEY = "mf_chat_threads_v1";
const btn = document.getElementById("sendBtn");
const msgInput = document.getElementById("msg");
const threadsList = document.getElementById("threadsList");
const activeThreadIdEl = document.getElementById("activeThreadId");
const messagesEl = document.getElementById("messages");
const newThreadBtn = document.getElementById("newThreadBtn");

let state = loadState();

if (!state.activeThreadId || !state.threads[state.activeThreadId]) {
  const id = createThread();
  state.activeThreadId = id;
  saveState();
}

renderAll();

newThreadBtn.addEventListener("click", () => {
  const id = createThread();
  state.activeThreadId = id;
  saveState();
  renderAll();
});

btn.addEventListener("click", async () => {
  const text = msgInput.value.trim();
  if (!text) {
    return;
  }
  const thread = state.threads[state.activeThreadId];
  pushMessage(thread.id, "user", text);
  msgInput.value = "";
  renderAll();

  try {
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: thread.id,
        message: text,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      const errText = data.answer || data.error || `Request failed (${resp.status})`;
      pushMessage(thread.id, "bot", errText, { citationUrl: data.citation_url || "" });
      saveState();
      renderAll();
      return;
    }
    const botText = data.answer || JSON.stringify(data, null, 2);
    pushMessage(thread.id, "bot", botText, { citationUrl: data.citation_url || "" });
    thread.lastPreview = botText.slice(0, 80);
    saveState();
    renderAll();
  } catch (err) {
    pushMessage(thread.id, "bot", `Request failed: ${String(err)}`);
    saveState();
    renderAll();
  }
});

msgInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    btn.click();
  }
});

function createThread() {
  const id = crypto.randomUUID();
  state.threads[id] = {
    id,
    title: `Thread ${Object.keys(state.threads).length + 1}`,
    messages: [],
    lastPreview: "",
  };
  return id;
}

function pushMessage(threadId, role, text, options = {}) {
  const t = state.threads[threadId];
  const row = { role, text, at: Date.now() };
  if (options.citationUrl) {
    row.citationUrl = String(options.citationUrl).trim();
  }
  t.messages.push(row);
  t.messages = t.messages.slice(-100);
  t.lastPreview = text.slice(0, 80);
  saveState();
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { activeThreadId: null, threads: {} };
    const parsed = JSON.parse(raw);
    return parsed && parsed.threads ? parsed : { activeThreadId: null, threads: {} };
  } catch {
    return { activeThreadId: null, threads: {} };
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function renderAll() {
  renderThreadList();
  renderMessages();
}

function renderThreadList() {
  const ids = Object.keys(state.threads);
  threadsList.innerHTML = "";
  ids.forEach((id) => {
    const t = state.threads[id];
    const item = document.createElement("div");
    item.className = `thread-item ${id === state.activeThreadId ? "active" : ""}`;
    item.innerHTML = `
      <div class="thread-title">${escapeHtml(t.title)}</div>
      <div class="thread-preview">${escapeHtml(t.lastPreview || "No messages yet")}</div>
    `;
    item.addEventListener("click", () => {
      state.activeThreadId = id;
      saveState();
      renderAll();
    });
    threadsList.appendChild(item);
  });
}

function renderMessages() {
  const t = state.threads[state.activeThreadId];
  activeThreadIdEl.textContent = t ? t.id : "";
  messagesEl.innerHTML = "";
  if (!t) return;
  t.messages.forEach((m) => {
    const div = document.createElement("div");
    div.className = `bubble ${m.role === "user" ? "user" : "bot"}`;
    if (m.role === "user") {
      div.textContent = m.text;
    } else {
      div.innerHTML = buildBotMessageHtml(m.text, m.citationUrl);
    }
    messagesEl.appendChild(div);
  });
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/**
 * http(s) URLs in bot answers become clickable; rest is escaped. Newlines → <br>.
 * Matches the three-line style: answer / Source: https://... / Last updated: ...
 */
function buildBotMessageHtml(plain, citationUrl) {
  const body = linkifyToSafeHtml(plain);
  const u = citationUrl && String(citationUrl).trim();
  if (u && /^https?:\/\//i.test(u)) {
    return (
      body +
      `<p class="source-cta" role="contentinfo" aria-label="Official source">` +
      `<a class="source-link source-link-cta" href="${escapeAttrHref(
        u,
      )}" target="_blank" rel="noopener noreferrer">Open official page</a></p>`
    );
  }
  return body;
}

function linkifyToSafeHtml(plain) {
  const s = String(plain);
  const urlRe = /(https?:\/\/[^\s)<]+)/gi;
  const parts = s.split(urlRe);
  return parts
    .map((part) => {
      if (/^https?:\/\//i.test(part)) {
        const href = part.replace(/[.,;]+$/g, "");
        return sourceAnchorHtml(href, escapeHtml(href));
      }
      return escapeHtml(part);
    })
    .join("")
    .replace(/\n/g, "<br>");
}

function sourceAnchorHtml(href, labelHtml) {
  return (
    `<a class="source-link" href="${escapeAttrHref(
      href,
    )}" target="_blank" rel="noopener noreferrer" tabindex="0">${labelHtml}</a>`
  );
}

function escapeAttrHref(s) {
  return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
