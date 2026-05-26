// Chat functionality for Agente AgroVision
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");
let chatHistory = [];
let currentFrameUrl = null;

const DASHBOARD_ENDPOINTS = {
  chat: "/dashboard/chat",
  events: "/dashboard/events",
  frame: "/dashboard/frame",
};

function apiFetch(url, options = {}) {
  return fetch(url, options);
}

function getEvidencePath(imagePath) {
  if (typeof imagePath === "string" && imagePath.startsWith("/static/captures/")) {
    return imagePath;
  }

  return "";
}

function addMessage(content, isUser = false) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `chat-message ${isUser ? 'user' : 'agent'}`;
  messageDiv.textContent = content;
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChatMessage() {
  const question = chatInput.value.trim();
  if (!question) return;

  addMessage(question, true);
  chatInput.value = '';

  try {
    const response = await apiFetch(DASHBOARD_ENDPOINTS.chat, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: question,
        history: chatHistory
      })
    });

    if (!response.ok) {
      throw new Error('Falha na resposta do agente');
    }

    const data = await response.json();
    addMessage(data.response, false);

    // Update history
    chatHistory.push({role: 'user', content: question});
    chatHistory.push({role: 'assistant', content: data.response});

    // Keep history limited
    if (chatHistory.length > 16) {
      chatHistory = chatHistory.slice(-16);
    }

  } catch (error) {
    addMessage('Erro: Não foi possível obter resposta do agente.', false);
    console.error('Chat error:', error);
  }
}

chatSend.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    sendChatMessage();
  }
});

// Existing functionality
const frame = document.getElementById("camera-frame");
const eventsTableBody = document.querySelector("#events-table tbody");

async function refreshFrame() {
  try {
    const response = await apiFetch(DASHBOARD_ENDPOINTS.frame + "?t=" + Date.now());
    if (!response.ok) return;

    const blob = await response.blob();
    const nextFrameUrl = URL.createObjectURL(blob);
    frame.src = nextFrameUrl;

    if (currentFrameUrl) {
      URL.revokeObjectURL(currentFrameUrl);
    }

    currentFrameUrl = nextFrameUrl;
  } catch (_) {
  }
}

function renderEvents(events) {
  eventsTableBody.innerHTML = "";
  for (const event of events) {
    const tr = document.createElement("tr");

    const eventTime = document.createElement("td");
    eventTime.textContent = event.event_time;

    const label = document.createElement("td");
    label.textContent = event.label;

    const confidence = document.createElement("td");
    const confidenceValue = Number(event.confidence);
    confidence.textContent = Number.isFinite(confidenceValue)
      ? confidenceValue.toFixed(2)
      : "-";

    const evidence = document.createElement("td");
    const evidencePath = getEvidencePath(event.image_path);
    if (evidencePath) {
      const link = document.createElement("a");
      link.href = evidencePath;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "abrir";
      evidence.appendChild(link);
    } else {
      evidence.textContent = "-";
    }

    tr.append(eventTime, label, confidence, evidence);
    eventsTableBody.appendChild(tr);
  }
}

async function refreshEvents() {
  try {
    const response = await apiFetch(DASHBOARD_ENDPOINTS.events);
    if (!response.ok) return;
    const events = await response.json();
    renderEvents(events);
  } catch (_) {
  }
}

refreshFrame();
refreshEvents();
setInterval(refreshFrame, 500);
setInterval(refreshEvents, 3000);
