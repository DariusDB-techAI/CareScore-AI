const state = {
    conversationId: "default",
    messages: [],
};

const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const modelBadge = document.getElementById("modelBadge");
const criteriaConfig = (window.APP_BOOTSTRAP && Array.isArray(window.APP_BOOTSTRAP.criteria))
    ? window.APP_BOOTSTRAP.criteria
    : [];
const criteriaById = Object.fromEntries(criteriaConfig.map((item) => [item.id, item]));

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderMessages() {
    const systemBlock = `
        <div class="message message--system">
            <div class="message__label">System</div>
            <div class="message__bubble">
                Nhap hoi thoai, kich mot tieu chi ben duoi, hoac yeu cau chatbot review cau tra loi theo muc tieu ban chon.
            </div>
        </div>
    `;

    const chatBlocks = state.messages.map((message) => `
        <div class="message message--${escapeHtml(message.role)}">
            <div class="message__label">${message.role === "user" ? "You" : "Gemini"}</div>
            <div class="message__bubble">${escapeHtml(message.content)}</div>
            ${renderAgentResult(message.agent_result)}
        </div>
    `).join("");

    messagesEl.innerHTML = systemBlock + chatBlocks;
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderAgentResult(agentResult) {
    if (!agentResult || !agentResult.criteria) {
        return "";
    }

    const cards = Object.values(agentResult.criteria).map((item) => `
        <div class="agent-card">
            <div class="agent-card__top">
                <strong>${escapeHtml(item.label)}</strong>
                <span>${escapeHtml(String(item.score))}/5</span>
            </div>
            <p>${escapeHtml(item.summary || "")}</p>
            <div class="agent-card__meta">
                <span>${escapeHtml(item.status || "")}</span>
                <span>${Math.round(Number(item.confidence || 0) * 100)}%</span>
            </div>
        </div>
    `).join("");

    const actions = Array.isArray(agentResult.improvement_actions)
        ? agentResult.improvement_actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
        : "";

    return `
        <section class="agent-result">
            <div class="agent-result__header">
                <strong>Agent evaluation</strong>
                <span>${escapeHtml(String(agentResult.overall_score || 0))}/5</span>
            </div>
            <p class="agent-result__summary">${escapeHtml(agentResult.summary || "")}</p>
            <p class="agent-result__summary">${escapeHtml(agentResult.coaching_note || "")}</p>
            <div class="agent-grid">${cards}</div>
            ${actions ? `<ul class="agent-actions">${actions}</ul>` : ""}
        </section>
    `;
}

function openCriterionPage(criterion) {
    const config = criteriaById[criterion];
    if (!config || !config.href) {
        window.alert(`Criterion page for "${criterion}" is not configured yet.`);
        return;
    }

    if (!config.has_page) {
        window.alert(
            `${config.label} chua co trang con hoan chinh. Team co the giu nguyen function openCriterionPage("${criterion}") va tao page sau theo dung pattern nay.`,
        );
        return;
    }

    window.location.href = config.href;
}

function fillCriterionPrompt(criterion) {
    const config = criteriaById[criterion];
    if (!config || !config.prompt) {
        return;
    }

    messageInput.value = config.prompt;
    messageInput.focus();
    messageInput.dispatchEvent(new Event("input"));
}

async function loadConfig() {
    const response = await fetch("/api/config");
    const payload = await response.json();
    if (!payload.configured) {
        modelBadge.textContent = `Gemini chua cau hinh | ${payload.model}`;
        return;
    }
    modelBadge.textContent = `Gemini | ${payload.model}`;
}

async function sendMessage(message) {
    sendButton.disabled = true;

    const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            conversation_id: state.conversationId,
            message,
        }),
    });

    const payload = await response.json();
    sendButton.disabled = false;

    if (!response.ok) {
        throw new Error(payload.error || "Could not send message.");
    }

    state.conversationId = payload.conversation_id;
    state.messages = payload.messages || [];
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
        state.messages.push({
            role: "assistant",
            content: `Loi: ${error.message}`,
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

document.querySelectorAll(".criterion-card").forEach((button) => {
    button.addEventListener("click", () => {
        const criterion = button.dataset.criterion || "";
        if (criterion) {
            openCriterionPage(criterion);
            return;
        }

        const prompt = button.dataset.prompt || "";
        if (prompt) {
            messageInput.value = prompt;
            messageInput.focus();
            messageInput.dispatchEvent(new Event("input"));
        }
    });
});

window.openCriterionPage = openCriterionPage;
window.fillCriterionPrompt = fillCriterionPrompt;

renderMessages();
loadConfig().catch(() => {
    modelBadge.textContent = "Khong doc duoc Gemini config";
});
