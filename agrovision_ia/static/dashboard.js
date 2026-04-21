// Chat functionality for Agente AgroVision
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");
let chatHistory = [];

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
    const response = await fetch('/chat', {
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

function refreshFrame() {
  frame.src = "/frame?t=" + Date.now();
}

function renderEvents(events) {
  eventsTableBody.innerHTML = "";
  for (const event of events) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${event.event_time}</td>
      <td>${event.label}</td>
      <td>${Number(event.confidence).toFixed(2)}</td>
      <td><a href="${event.image_path}" target="_blank">abrir</a></td>
    `;
    eventsTableBody.appendChild(tr);
  }
}

async function refreshEvents() {
  try {
    const response = await fetch("/events");
    if (!response.ok) return;
    const events = await response.json();
    renderEvents(events);
  } catch (_) {
  }
}

setInterval(refreshFrame, 500);
setInterval(refreshEvents, 3000);