const toxicityChatConfig = window.CRITERION_CHAT_CONFIG || {};

const toxicityState = {
  conversationId: "default",
  messages: [],
};

const messagesEl = document.getElementById("toxicityMessages");
const chatForm = document.getElementById("toxicityForm");
const messageInput = document.getElementById("toxicityInput");
const sendButton = document.getElementById("toxicitySendButton");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderAgentResult(agentResult) {
  if (!agentResult || !agentResult.criterion) {
    return "";
  }

  const probabilities = Object.entries(agentResult.probabilities || {})
    .map(
      ([label, score]) =>
        `<li>${escapeHtml(label)} : ${Math.round(Number(score) * 100)}%</li>`,
    )
    .join("");

  return `
        <section class="agent-result">

            <div class="agent-result__header">
                <strong>${escapeHtml(agentResult.criterion)}</strong>
                <span>${escapeHtml(String(agentResult.score || 0))}/5</span>
            </div>

            <p class="agent-result__summary">
                ${escapeHtml(agentResult.summary || "")}
            </p>

            <div class="agent-grid">

                <div class="agent-card">

                    <div class="agent-card__top">
                        <strong>Prediction</strong>
                        <span>${escapeHtml(agentResult.raw_label || "")}</span>
                    </div>

                    <div class="agent-card__meta">
                        <span>${escapeHtml(agentResult.status || "")}</span>

                        <span>
                            ${Math.round(
                              Number(agentResult.confidence || 0) * 100,
                            )}%
                        </span>
                    </div>

                </div>

                <div class="agent-card">

                    <div class="agent-card__top">
                        <strong>Model</strong>
                        <span>
                            ${escapeHtml(agentResult.model_hint || "PhoBERT")}
                        </span>
                    </div>

                    ${
                      probabilities
                        ? `<ul class="agent-actions">${probabilities}</ul>`
                        : ""
                    }

                </div>

            </div>

        </section>
    `;
}

function renderMessages() {
  const systemBlock = `
        <div class="message message--system">

            <div class="message__label">
                System
            </div>

            <div class="message__bubble">
                Chào mừng bạn đến với Toxicity Agent.
                Hệ thống chỉ sử dụng mô hình Toxicity
                để phân tích hội thoại.
            </div>

        </div>
    `;

  const chatBlocks = toxicityState.messages
    .map(
      (message) => `

        <div class="message message--${escapeHtml(message.role)}">

            <div class="message__label">

                ${
                  message.role === "user"
                    ? "You"
                    : toxicityChatConfig.title || "Toxicity Agent"
                }

            </div>

            <div class="message__bubble">

                ${escapeHtml(message.content)}

            </div>

            ${renderAgentResult(message.agent_result)}

        </div>

    `,
    )
    .join("");

  messagesEl.innerHTML = systemBlock + chatBlocks;

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(message) {
  sendButton.disabled = true;

  const response = await fetch(toxicityChatConfig.endpoint, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      conversation_id: toxicityState.conversationId,
      message,
    }),
  });

  const payload = await response.json();

  sendButton.disabled = false;

  if (!response.ok) {
    throw new Error(payload.error || "Could not send message.");
  }

  toxicityState.conversationId = payload.conversation_id;

  toxicityState.messages = payload.messages || [];

  renderMessages();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();

  if (!message) {
    return;
  }

  try {
    await sendMessage(message);

    messageInput.value = "";

    messageInput.style.height = "72px";
  } catch (error) {
    toxicityState.messages.push({
      role: "assistant",

      content: `Lỗi: ${error.message}`,
    });

    renderMessages();
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";

  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 220)}px`;
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();

    chatForm.requestSubmit();
  }
});

renderMessages();
