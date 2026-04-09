const conversationEndpoint = "/api/v1/conversation/message";

const messagesElement = document.querySelector("#messages");
const formElement = document.querySelector("#chat-form");
const inputElement = document.querySelector("#message-input");
const sendButtonElement = document.querySelector("#send-button");
const newChatButtonElement = document.querySelector("#new-chat-button");
const sessionIdElement = document.querySelector("#session-id");
const statusBadgeElement = document.querySelector("#status-badge");

let sessionId = window.localStorage.getItem("asisOperational.sessionId") || "";

function updateSessionLabel() {
  sessionIdElement.textContent = sessionId || "Sin sesión activa";
}

function setStatus(text, isError = false) {
  statusBadgeElement.textContent = text;
  statusBadgeElement.classList.toggle("error", isError);
}

function clearEmptyState() {
  const emptyState = messagesElement.querySelector(".empty-state");
  if (emptyState) {
    emptyState.remove();
  }
}

const structuredLabels = [
  "Estado",
  "Falla",
  "Impacto",
  "SMS/bitácora original",
  "SMS/bitacora original",
  "Solucionado",
  "Hora de solución",
  "HORA DE SOLUCIÓN",
];

const duplicatedSmsLabels = new Set(["estado", "falla", "impacto"]);

function appendPlainText(parentElement, text) {
  const paragraphElement = document.createElement("p");
  paragraphElement.textContent = improveTextBreaks(text);
  parentElement.appendChild(paragraphElement);
}

function appendValue(parentElement, text) {
  const paragraphElement = document.createElement("p");
  paragraphElement.textContent = improveTextBreaks(text);
  parentElement.appendChild(paragraphElement);
}

function stripMarkdown(text) {
  return text.replace(/\*\*/g, "").replace(/^\s*[-*]\s*/, "").trim();
}

function normalizeLabel(label) {
  return label
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function improveTextBreaks(text) {
  return text
    .replace(/\s+\|\s+/g, "\n")
    .replace(/\s+(\d+\.\s+\d{1,2}:\d{2}\s+-\s+)/g, "\n$1")
    .replace(/\s+(\[[A-ZÁÉÍÓÚÑ ]+\])/g, "\n$1")
    .replace(/\s+(\*\d{1,2}:\d{2}\s*hrs)/gi, "\n$1")
    .trim();
}

function splitStructuredAssistantText(text) {
  const markerPattern = new RegExp(
    `\\s*(${structuredLabels
      .map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .join("|")}):\\s*`,
    "gi",
  );
  const segments = [];
  let currentLabel = "";
  let currentStart = 0;
  let match;

  while ((match = markerPattern.exec(text)) !== null) {
    if (!currentLabel) {
      const introText = text.slice(0, match.index).trim();
      if (introText) {
        segments.push({ label: "", value: introText });
      }
    } else {
      const value = text.slice(currentStart, match.index).trim();
      segments.push({ label: currentLabel, value });
    }

    currentLabel = match[1];
    currentStart = markerPattern.lastIndex;
  }

  if (currentLabel) {
    segments.push({
      label: currentLabel,
      value: text.slice(currentStart).trim(),
    });
  }

  return segments;
}

function hasSmsOriginal(segments) {
  return segments.some((segment) =>
    normalizeLabel(segment.label).startsWith("sms/bitacora original"),
  );
}

function splitSmsSections(text) {
  const tagPattern = /\s*\[(FALLA|IMPACTO|SOLUCIONADO|HORA DE SOLUCIÓN)\]\s*/gi;
  const sections = [];
  let currentLabel = "";
  let currentStart = 0;
  let match;

  while ((match = tagPattern.exec(text)) !== null) {
    if (currentLabel) {
      const value = text.slice(currentStart, match.index).trim();
      sections.push({ label: currentLabel, value });
    }

    currentLabel = match[1];
    currentStart = tagPattern.lastIndex;
  }

  if (currentLabel) {
    sections.push({ label: currentLabel, value: text.slice(currentStart).trim() });
  }

  return sections;
}

function splitResolutionEvents(text) {
  return text
    .split(/\s*(?=\*\d{1,2}:\d{2}\s*hrs)/gi)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => item.replace(/^\*/, ""));
}

function appendSmsOriginal(parentElement, text) {
  const sections = splitSmsSections(text);

  if (sections.length === 0) {
    appendValue(parentElement, text);
    return;
  }

  const smsElement = document.createElement("div");
  smsElement.className = "sms-sections";

  for (const section of sections) {
    const itemElement = document.createElement("section");
    itemElement.className = "sms-section";

    const labelElement = document.createElement("h4");
    labelElement.textContent = section.label;
    itemElement.appendChild(labelElement);

    if (normalizeLabel(section.label) === "solucionado") {
      const events = splitResolutionEvents(section.value);
      const listElement = document.createElement("ul");

      for (const event of events) {
        const listItemElement = document.createElement("li");
        listItemElement.textContent = improveTextBreaks(event);
        listElement.appendChild(listItemElement);
      }

      itemElement.appendChild(listElement);
    } else {
      appendValue(itemElement, section.value);
    }

    smsElement.appendChild(itemElement);
  }

  parentElement.appendChild(smsElement);
}

function parseTimeline(text) {
  if (!/timeline|línea de tiempo|linea de tiempo/i.test(text)) {
    return null;
  }

  const rawParts = text
    .split(/\s+\|\s+|\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
  const introParts = [];
  const footerParts = [];
  const items = [];
  let startedItems = false;

  for (const part of rawParts) {
    const cleanedPart = stripMarkdown(part.replace(/^\d+\.\s*/, ""));
    const match = cleanedPart.match(
      /^(\d{1,2}:\d{2})(?:\s*hrs)?\s*(?:-|:)\s*(.+)$/i,
    );

    if (!match) {
      if (startedItems) {
        footerParts.push(cleanedPart);
      } else {
        introParts.push(cleanedPart);
      }
      continue;
    }

    startedItems = true;
    items.push({ time: match[1], description: match[2] });
  }

  return items.length
    ? {
        intro: introParts.join("\n\n"),
        items,
        footer: footerParts.join("\n\n"),
      }
    : null;
}

function appendTimeline(parentElement, text) {
  const timeline = parseTimeline(text);

  if (!timeline) {
    return false;
  }

  const contentElement = document.createElement("div");
  contentElement.className = "timeline-response";

  appendPlainText(contentElement, timeline.intro);

  const listElement = document.createElement("ol");

  for (const item of timeline.items) {
    const listItemElement = document.createElement("li");

    if (item.time) {
      const timeElement = document.createElement("strong");
      timeElement.textContent = `${item.time} hrs`;
      listItemElement.appendChild(timeElement);
    }

    const descriptionElement = document.createElement("span");
    descriptionElement.textContent = item.description;
    listItemElement.appendChild(descriptionElement);
    listElement.appendChild(listItemElement);
  }

  contentElement.appendChild(listElement);

  if (timeline.footer) {
    appendPlainText(contentElement, timeline.footer);
  }

  parentElement.appendChild(contentElement);
  return true;
}

function appendStructuredAssistantMessage(parentElement, text) {
  if (appendTimeline(parentElement, text)) {
    return;
  }

  const segments = splitStructuredAssistantText(text);

  if (segments.length < 2) {
    appendPlainText(parentElement, text);
    return;
  }

  const contentElement = document.createElement("div");
  contentElement.className = "structured-response";
  const responseHasSmsOriginal = hasSmsOriginal(segments);

  for (const segment of segments) {
    if (!segment.value) {
      continue;
    }

    if (
      responseHasSmsOriginal &&
      duplicatedSmsLabels.has(normalizeLabel(segment.label))
    ) {
      continue;
    }

    if (!segment.label) {
      appendPlainText(contentElement, segment.value);
      continue;
    }

    const itemElement = document.createElement("section");
    itemElement.className = "response-field";

    const labelElement = document.createElement("h3");
    labelElement.textContent = segment.label;

    itemElement.appendChild(labelElement);

    if (normalizeLabel(segment.label).startsWith("sms/bitacora original")) {
      appendSmsOriginal(itemElement, segment.value);
    } else {
      appendValue(itemElement, segment.value);
    }

    contentElement.appendChild(itemElement);
  }

  parentElement.appendChild(contentElement);
}

function addMessage(role, text) {
  clearEmptyState();

  const messageElement = document.createElement("article");
  messageElement.className = `message ${role}`;

  const bubbleElement = document.createElement("div");
  bubbleElement.className = "bubble";

  if (role === "assistant") {
    appendStructuredAssistantMessage(bubbleElement, text);
  } else {
    bubbleElement.textContent = text;
  }

  messageElement.appendChild(bubbleElement);
  messagesElement.appendChild(messageElement);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function resetComposerHeight() {
  inputElement.style.height = "auto";
  inputElement.style.height = `${Math.min(inputElement.scrollHeight, 176)}px`;
}

function startNewChat() {
  sessionId = "";
  window.localStorage.removeItem("asisOperational.sessionId");
  updateSessionLabel();
  setStatus("Listo");

  messagesElement.innerHTML = `
    <div class="empty-state">
      <h2>¿En qué puedo ayudarte?</h2>
      <p>Inicia una consulta operacional.</p>
    </div>
  `;

  inputElement.value = "";
  resetComposerHeight();
  inputElement.focus();
}

async function sendMessage(message) {
  const payload = {
    message,
    mode: "general",
    requested_capabilities: ["session_memory"],
  };

  if (sessionId) {
    payload.session_id = sessionId;
  }

  const response = await fetch(conversationEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  let responseBody;
  try {
    responseBody = await response.json();
  } catch {
    responseBody = {};
  }

  if (!response.ok) {
    const detail = responseBody.detail || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return responseBody;
}

formElement.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = inputElement.value.trim();
  if (!message) {
    return;
  }

  addMessage("user", message);
  inputElement.value = "";
  resetComposerHeight();
  sendButtonElement.disabled = true;
  setStatus("Pensando...");

  try {
    const responseBody = await sendMessage(message);
    sessionId = responseBody.session_id || sessionId;

    if (sessionId) {
      window.localStorage.setItem("asisOperational.sessionId", sessionId);
    }

    updateSessionLabel();
    addMessage("assistant", responseBody.response_text || "Sin respuesta.");
    setStatus(responseBody.status || "Completado");
  } catch (error) {
    addMessage("error", `No se pudo procesar el mensaje: ${error.message}`);
    setStatus("Error", true);
  } finally {
    sendButtonElement.disabled = false;
    inputElement.focus();
  }
});

inputElement.addEventListener("input", resetComposerHeight);

inputElement.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    formElement.requestSubmit();
  }
});

newChatButtonElement.addEventListener("click", startNewChat);

updateSessionLabel();
resetComposerHeight();
