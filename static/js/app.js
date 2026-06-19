const criteriaConfig = (window.APP_BOOTSTRAP && Array.isArray(window.APP_BOOTSTRAP.criteria))
    ? window.APP_BOOTSTRAP.criteria
    : [];
const criteriaById = Object.fromEntries(criteriaConfig.map((item) => [item.id, item]));

const state = {
    conversationId: createConversationId(),
    conversations: [],
    messages: [],
    currentConversation: null,
    latestEvaluation: null,
    latestAdvisorContext: null,
    selectedEvaluationCriteria: [],
    socket: null,
    socketReady: false,
    pendingRequests: new Map(),
};

const messagesEl = document.getElementById("messages");
const recentListEl = document.getElementById("recentList");
const insightCriteriaEl = document.getElementById("insightCriteria");
const criteriaDockEl = document.getElementById("criteriaDock");
const evaluatorCriteriaEl = document.getElementById("evaluatorCriteria");
const evaluatorPlanMetaEl = document.getElementById("evaluatorPlanMeta");
const connectionBadge = document.getElementById("connectionBadge");
const modelBadge = document.getElementById("modelBadge");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const newChatButton = document.getElementById("newChatButton");
const evaluatorForm = document.getElementById("evaluatorForm");
const evaluatorInput = document.getElementById("evaluatorInput");
const evaluatorButton = document.getElementById("evaluatorButton");

function createConversationId() {
    return `conversation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatTime(value) {
    if (!value) {
        return "";
    }

    try {
        return new Date(value).toLocaleString("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
            day: "2-digit",
            month: "2-digit",
        });
    } catch {
        return "";
    }
}

function renderEmptyState() {
    messagesEl.innerHTML = `
        <section class="empty-state">
            <div class="empty-state__content">
                <span class="hub-label">Bat dau</span>
                <h3>Hoi nhu mot khach hang dang mua sam tai FPT Shop.</h3>
                <p>
                    Ban co the hoi ve dien thoai, laptop, phu kien, tra gop, bao hanh, hoac yeu cau danh gia chat luong hoi thoai.
                </p>
            </div>
        </section>
    `;
}

function renderMessages() {
    if (!state.messages.length) {
        renderEmptyState();
        return;
    }

    const markup = state.messages.map((message) => {
        const isUser = message.role === "user";
        const timestamp = formatTime(message.created_at);
        return `
            <article class="chat-message chat-message--${escapeHtml(message.role)}">
                <div class="chat-message__avatar">${isUser ? "KH" : "FPT"}</div>
                <div class="chat-message__body">
                    <div class="chat-message__role">${isUser ? "Khach" : "Tu van vien"}</div>
                    <div class="chat-message__bubble">${escapeHtml(message.content)}</div>
                    ${timestamp ? `<div class="chat-message__meta">${escapeHtml(timestamp)}</div>` : ""}
                </div>
            </article>
        `;
    }).join("");

    messagesEl.innerHTML = markup;
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderRecentList() {
    if (!state.conversations.length) {
        recentListEl.innerHTML = `<div class="recent-empty">Chua co hoi thoai nao.</div>`;
        return;
    }

    recentListEl.innerHTML = state.conversations.map((conversation) => `
        <button
            class="recent-item ${conversation.id === state.conversationId ? "is-active" : ""}"
            type="button"
            data-conversation-id="${escapeHtml(conversation.id)}"
        >
            <strong>${escapeHtml(conversation.title || "Cuoc hoi thoai moi")}</strong>
            <span>${escapeHtml(conversation.preview || "Chua co preview")}</span>
            <small>${escapeHtml(formatTime(conversation.updated_at))}</small>
        </button>
    `).join("");

    recentListEl.querySelectorAll("[data-conversation-id]").forEach((button) => {
        button.addEventListener("click", async () => {
            const conversationId = button.getAttribute("data-conversation-id") || "";
            if (!conversationId || conversationId === state.conversationId) {
                return;
            }

            try {
                const response = await sendSocketRequest("load_conversation", { conversation_id: conversationId });
                const conversation = response.conversation || {};
                state.conversationId = conversation.id || conversationId;
                state.messages = Array.isArray(conversation.messages) ? conversation.messages : [];
                state.currentConversation = conversation;
                state.latestEvaluation = conversation.latest_agent_result || null;
                state.latestAdvisorContext = conversation.latest_advisor_context || null;
                renderMessages();
                renderInsights();
                renderRecentList();
            } catch (error) {
                pushLocalError(error.message);
            }
        });
    });
}

function renderInsights() {
    const evaluation = state.latestEvaluation;
    const conversation = state.currentConversation || {};
    const advisorContext = state.latestAdvisorContext || conversation.latest_advisor_context || null;

    if (!evaluation) {
        evaluatorPlanMetaEl.textContent = advisorContext
            ? `Nguon: ${advisorContext.source || "https://fptshop.com.vn/"}`
            : "Nguon tham chieu chinh: https://fptshop.com.vn/";
    } else {
        const orchestrator = evaluation.orchestrator || {};
        const routed = Array.isArray(orchestrator.selected_criteria) ? orchestrator.selected_criteria.join(", ") : "none";
        const source = orchestrator.source || "runtime";
        evaluatorPlanMetaEl.textContent = `Routed: ${routed} | Source: ${source}`;
    }

    if (!evaluation && advisorContext) {
        const snippets = Array.isArray(advisorContext.snippets) ? advisorContext.snippets.slice(0, 6) : [];
        insightCriteriaEl.innerHTML = snippets.length
            ? snippets.map((snippet, index) => `
                <article class="insight-card">
                    <div class="insight-card__head">
                        <div class="criterion-badge">0${index + 1}</div>
                        <div class="insight-card__title">
                            <h4>Snippet FPT Shop</h4>
                            <span>${escapeHtml(advisorContext.homepage_status || "ready")}</span>
                        </div>
                    </div>
                    <p>${escapeHtml(snippet)}</p>
                </article>
            `).join("")
            : `<div class="recent-empty">Chua lay duoc snippet tu FPT Shop luc nay.</div>`;
        return;
    }

    if (!evaluation) {
        insightCriteriaEl.innerHTML = `<div class="recent-empty">Context FPT Shop se hien thi sau khi co luot tu van.</div>`;
        return;
    }

    insightCriteriaEl.innerHTML = criteriaConfig.map((criterion, index) => {
        const result = evaluation && evaluation.criteria ? evaluation.criteria[criterion.id] : null;
        const score = result ? `${result.score}/5` : "--/5";
        const summary = result ? result.summary : "";
        const confidence = result ? `${Math.round(Number(result.confidence || 0) * 100)}%` : "--";
        const status = result ? result.status : "idle";
        const detailAction = criterion.has_page
            ? `<button class="criterion-link" type="button" data-open-criterion="${escapeHtml(criterion.id)}">Open</button>`
            : "";

        return `
            <article class="insight-card">
                <div class="insight-card__head">
                    <div class="criterion-badge">0${index + 1}</div>
                    <div class="insight-card__title">
                        <h4>${escapeHtml(criterion.label)}</h4>
                        <span>${escapeHtml(status)}</span>
                    </div>
                    <strong class="insight-score">${escapeHtml(score)}</strong>
                </div>
                ${summary ? `<p>${escapeHtml(summary)}</p>` : ""}
                <div class="insight-card__meta">
                    <span>Confidence ${escapeHtml(confidence)}</span>
                    <button class="criterion-link" type="button" data-fill-criterion="${escapeHtml(criterion.id)}">Prompt</button>
                    ${detailAction}
                </div>
            </article>
        `;
    }).join("");

    insightCriteriaEl.querySelectorAll("[data-fill-criterion]").forEach((button) => {
        button.addEventListener("click", () => {
            fillCriterionPrompt(button.getAttribute("data-fill-criterion") || "");
        });
    });

    insightCriteriaEl.querySelectorAll("[data-open-criterion]").forEach((button) => {
        button.addEventListener("click", () => {
            openCriterionPage(button.getAttribute("data-open-criterion") || "");
        });
    });
}

function renderCriteriaDock() {
    criteriaDockEl.innerHTML = criteriaConfig.map((criterion, index) => `
        <button
            class="criteria-option"
            type="button"
            data-open-criterion="${escapeHtml(criterion.id)}"
        >
            <span class="criteria-option__index">0${index + 1}</span>
            <strong>${escapeHtml(criterion.label)}</strong>
        </button>
    `).join("");

    criteriaDockEl.querySelectorAll("[data-open-criterion]").forEach((button) => {
        button.addEventListener("click", () => {
            openCriterionPage(button.getAttribute("data-open-criterion") || "");
        });
    });
}

function renderEvaluatorCriteria() {
    evaluatorCriteriaEl.innerHTML = criteriaConfig.map((criterion) => `
        <button
            class="evaluator-chip ${state.selectedEvaluationCriteria.includes(criterion.id) ? "is-active" : ""}"
            type="button"
            data-evaluator-criterion="${escapeHtml(criterion.id)}"
        >
            ${escapeHtml(criterion.label)}
        </button>
    `).join("");

    evaluatorCriteriaEl.querySelectorAll("[data-evaluator-criterion]").forEach((button) => {
        button.addEventListener("click", () => {
            const criterionId = button.getAttribute("data-evaluator-criterion") || "";
            toggleEvaluationCriterion(criterionId);
        });
    });
}

function toggleEvaluationCriterion(criterionId) {
    if (!criterionId) {
        return;
    }

    if (state.selectedEvaluationCriteria.includes(criterionId)) {
        state.selectedEvaluationCriteria = state.selectedEvaluationCriteria.filter((item) => item !== criterionId);
    } else {
        state.selectedEvaluationCriteria = [...state.selectedEvaluationCriteria, criterionId];
    }

    if (state.selectedEvaluationCriteria.length === 1) {
        const criterion = criteriaById[state.selectedEvaluationCriteria[0]];
        if (criterion && !evaluatorInput.value.trim()) {
            evaluatorInput.value = `Review this conversation for ${criterion.label.toLowerCase()}.`;
        }
    }

    renderEvaluatorCriteria();
    if (state.messages.length) {
        runEvaluatorRequest().catch((error) => {
            pushLocalError(error.message);
        });
    }
}

function upsertConversationSummary(conversation) {
    if (!conversation || !conversation.id) {
        return;
    }

    const next = state.conversations.filter((item) => item.id !== conversation.id);
    next.unshift({
        id: conversation.id,
        title: conversation.title || "Cuoc hoi thoai moi",
        preview: conversation.preview || "Chua co preview",
        updated_at: conversation.updated_at || new Date().toISOString(),
    });
    state.conversations = next;
}

function openCriterionPage(criterion) {
    const config = criteriaById[criterion];
    if (!config || !config.href) {
        window.alert(`Criterion page for "${criterion}" is not configured yet.`);
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

function pushLocalError(message) {
    state.messages.push({
        role: "assistant",
        content: `Loi: ${message}`,
    });
    renderMessages();
}

function setSocketStatus(ready, label) {
    state.socketReady = ready;
    connectionBadge.textContent = label;
    connectionBadge.classList.toggle("is-live", ready);
    sendButton.disabled = !ready;
    evaluatorButton.disabled = !ready;
}

function buildSocketUrl() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsPath = (window.APP_BOOTSTRAP && window.APP_BOOTSTRAP.wsPath) || "/ws/chat";
    return `${protocol}://${window.location.host}${wsPath}`;
}

function connectSocket() {
    const socket = new WebSocket(buildSocketUrl());
    state.socket = socket;
    setSocketStatus(false, "Dang ket noi websocket...");

    socket.addEventListener("open", async () => {
        setSocketStatus(true, "Websocket da san sang");
        try {
            const recentPayload = await sendSocketRequest("recent", {});
            state.conversations = Array.isArray(recentPayload.conversations) ? recentPayload.conversations : [];
            renderRecentList();
        } catch (error) {
            pushLocalError(error.message);
        }
    });

    socket.addEventListener("message", (event) => {
        let payload;
        try {
            payload = JSON.parse(event.data);
        } catch {
            return;
        }

        const requestId = payload.request_id;
        if (requestId && state.pendingRequests.has(requestId)) {
            const { resolve, reject } = state.pendingRequests.get(requestId);
            state.pendingRequests.delete(requestId);
            if (payload.type === "error") {
                reject(new Error(payload.error || "Websocket request failed."));
                return;
            }
            resolve(payload);
            return;
        }

        if (payload.type === "recent" && Array.isArray(payload.conversations)) {
            state.conversations = payload.conversations;
            renderRecentList();
        }
    });

    socket.addEventListener("close", () => {
        setSocketStatus(false, "Websocket da ngat. Dang thu ket noi lai...");
        for (const pending of state.pendingRequests.values()) {
            pending.reject(new Error("Websocket connection closed."));
        }
        state.pendingRequests.clear();
        window.setTimeout(connectSocket, 1200);
    });

    socket.addEventListener("error", () => {
        setSocketStatus(false, "Websocket gap loi");
    });
}

function sendSocketRequest(type, payload) {
    return new Promise((resolve, reject) => {
        if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
            reject(new Error("Websocket chua san sang."));
            return;
        }

        const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        state.pendingRequests.set(requestId, { resolve, reject });
        state.socket.send(JSON.stringify({ type, request_id: requestId, ...payload }));
    });
}

async function sendHubMessage(message) {
    sendButton.disabled = true;
    try {
        const payload = await sendSocketRequest("chat", {
            conversation_id: state.conversationId,
            message,
        });

        state.conversationId = payload.conversation_id || state.conversationId;
        state.messages = Array.isArray(payload.messages) ? payload.messages : [];
        state.currentConversation = payload.conversation || null;
        state.latestEvaluation = payload.conversation ? payload.conversation.latest_agent_result : null;
        state.latestAdvisorContext = payload.conversation ? payload.conversation.latest_advisor_context : null;
        if (payload.conversation) {
            upsertConversationSummary(payload.conversation);
        } else if (Array.isArray(payload.conversations)) {
            state.conversations = payload.conversations;
        }
        if (Array.isArray(payload.conversations)) {
            state.conversations = payload.conversations;
        }
        renderMessages();
        renderInsights();
        renderRecentList();
    } finally {
        sendButton.disabled = !state.socketReady;
    }
}

async function loadConfig() {
    const response = await fetch("/api/config");
    const payload = await response.json();
    modelBadge.textContent = payload.configured
        ? `Gemini | ${payload.model}`
        : `Gemini chua cau hinh | ${payload.model}`;
}

function startNewConversation() {
    state.conversationId = createConversationId();
    state.messages = [];
    state.currentConversation = null;
    state.latestEvaluation = null;
    state.latestAdvisorContext = null;
    state.selectedEvaluationCriteria = [];
    renderMessages();
    renderInsights();
    renderRecentList();
    renderEvaluatorCriteria();
    evaluatorInput.value = "";
    messageInput.value = "";
    messageInput.dispatchEvent(new Event("input"));
    messageInput.focus();
}

chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (!message) {
        return;
    }

    try {
        await sendHubMessage(message);
        messageInput.value = "";
        messageInput.style.height = "56px";
    } catch (error) {
        pushLocalError(error.message);
    }
});

messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 240)}px`;
});

messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});

newChatButton.addEventListener("click", () => {
    startNewConversation();
});

async function runEvaluatorRequest() {
    if (!state.messages.length) {
        throw new Error("Chua co hoi thoai de danh gia.");
    }

    evaluatorButton.disabled = true;
    try {
        const payload = await sendSocketRequest("evaluate", {
            conversation_id: state.conversationId,
            criteria: state.selectedEvaluationCriteria,
            prompt: evaluatorInput.value.trim(),
        });
        state.latestEvaluation = payload.evaluation || null;
        state.currentConversation = payload.conversation || state.currentConversation;
        state.messages = Array.isArray(payload.messages)
            ? payload.messages
            : Array.isArray(payload.conversation && payload.conversation.messages)
                ? payload.conversation.messages
                : state.messages;
        if (payload.conversation) {
            upsertConversationSummary(payload.conversation);
        } else if (Array.isArray(payload.conversations)) {
            state.conversations = payload.conversations;
        }
        if (Array.isArray(payload.conversations)) {
            state.conversations = payload.conversations;
        }
        renderMessages();
        renderInsights();
        renderRecentList();
    } finally {
        evaluatorButton.disabled = !state.socketReady;
    }
}

evaluatorForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        await runEvaluatorRequest();
    } catch (error) {
        pushLocalError(error.message);
    }
});

window.openCriterionPage = openCriterionPage;
window.fillCriterionPrompt = fillCriterionPrompt;
window.sendHubMessage = sendHubMessage;

renderMessages();
renderInsights();
renderRecentList();
renderCriteriaDock();
renderEvaluatorCriteria();
loadConfig().catch(() => {
    modelBadge.textContent = "Khong doc duoc Gemini config";
});
connectSocket();
