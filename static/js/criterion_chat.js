const criterionChatConfig = window.CRITERION_CHAT_CONFIG || {};
const criterionState = {
    conversationId: "default",
    messages: [],
};

const criterionMessagesEl = document.getElementById("positivityMessages");
const criterionForm = document.getElementById("positivityForm");
const criterionInput = document.getElementById("positivityInput");
const criterionSendButton = document.getElementById("positivitySendButton");

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
        .map(([label, score]) => `<li>${escapeHtml(label)}: ${Math.round(Number(score) * 100)}%</li>`)
        .join("");

    return `
        <section class="agent-result">
            <div class="agent-result__header">
                <strong>${escapeHtml(agentResult.criterion)}</strong>
                <span>${escapeHtml(String(agentResult.score || 0))}/5</span>
            </div>
            <p class="agent-result__summary">${escapeHtml(agentResult.summary || "")}</p>
            <div class="agent-grid">
                <div class="agent-card">
                    <div class="agent-card__top">
                        <strong>Raw label</strong>
                        <span>${escapeHtml(agentResult.raw_label || "")}</span>
                    </div>
                    <div class="agent-card__meta">
                        <span>${escapeHtml(agentResult.status || "")}</span>
                        <span>${Math.round(Number(agentResult.confidence || 0) * 100)}%</span>
                    </div>
                </div>
                <div class="agent-card">
                    <div class="agent-card__top">
                        <strong>Model</strong>
                        <span>${escapeHtml(agentResult.model_hint || "")}</span>
                    </div>
                    ${probabilities ? `<ul class="agent-actions">${probabilities}</ul>` : ""}
                </div>
            </div>
        </section>
    `;
}

function renderMessages() {
    const systemBlock = `
        <div class="message message--system">
            <div class="message__label">System</div>
            <div class="message__bubble">
                Day la positivity chatbot. Moi ket qua se chi dung model positivity.
            </div>
        </div>
    `;

    const chatBlocks = criterionState.messages.map((message) => `
        <div class="message message--${escapeHtml(message.role)}">
            <div class="message__label">${message.role === "user" ? "You" : criterionChatConfig.title || "Agent"}</div>
            <div class="message__bubble">${escapeHtml(message.content)}</div>
            ${renderAgentResult(message.agent_result)}
        </div>
    `).join("");

    criterionMessagesEl.innerHTML = systemBlock + chatBlocks;
    criterionMessagesEl.scrollTop = criterionMessagesEl.scrollHeight;
}

async function sendCriterionMessage(message) {
    criterionSendButton.disabled = true;
    const response = await fetch(criterionChatConfig.endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            conversation_id: criterionState.conversationId,
            message,
        }),
    });
    const payload = await response.json();
    criterionSendButton.disabled = false;
    if (!response.ok) {
        throw new Error(payload.error || "Could not send message.");
    }
    criterionState.conversationId = payload.conversation_id;
    criterionState.messages = payload.messages || [];
    renderMessages();
}

criterionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = criterionInput.value.trim();
    if (!message) {
        return;
    }

    try {
        await sendCriterionMessage(message);
        criterionInput.value = "";
        criterionInput.style.height = "72px";
    } catch (error) {
        criterionState.messages.push({
            role: "assistant",
            content: `Loi: ${error.message}`,
        });
        renderMessages();
    }
});

criterionInput.addEventListener("input", () => {
    criterionInput.style.height = "auto";
    criterionInput.style.height = `${Math.min(criterionInput.scrollHeight, 220)}px`;
});

criterionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        criterionForm.requestSubmit();
    }
});

renderMessages();
