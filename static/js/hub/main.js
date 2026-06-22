import { criteriaById } from "./bootstrap.js";
import {
    chatForm,
    criteriaDockEl,
    evaluatorButton,
    evaluatorCriteriaEl,
    evaluatorForm,
    evaluatorInput,
    insightCriteriaEl,
    messageInput,
    modelBadge,
    newChatButton,
    recentListEl,
    sendButton,
} from "./dom.js";
import { buildSocketUrl, fetchConversationDetail, loadConfig, sendSocketRequest, setSocketStatus } from "./api.js";
import { renderCriteriaDock, renderEvaluatorCriteria, renderInsights, renderMessages, renderRecentList } from "./render.js";
import { state } from "./store.js";
import { buildTranscriptFromMessages, createConversationId } from "./utils.js";

function renderAll() {
    renderMessages(state);
    renderInsights(state);
    renderRecentList(state);
    renderEvaluatorCriteria(state);
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

    const transcript = buildTranscriptFromMessages(state.messages);
    if (transcript) {
        try {
            window.localStorage.setItem(`criterionDraft:${criterion}`, transcript);
        } catch {
            // Ignore storage errors and continue navigation.
        }
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
    state.messages.push({ role: "assistant", content: `Loi: ${message}` });
    renderMessages(state);
}

function connectSocket() {
    const socket = new WebSocket(buildSocketUrl());
    state.socket = socket;
    setSocketStatus(state, false, "Dang ket noi websocket...");

    socket.addEventListener("open", async () => {
        setSocketStatus(state, true, "Websocket da san sang");
        try {
            const recentPayload = await sendSocketRequest(state, "recent", {});
            state.conversations = Array.isArray(recentPayload.conversations) ? recentPayload.conversations : [];
            renderRecentList(state);
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
            renderRecentList(state);
        }
    });

    socket.addEventListener("close", () => {
        setSocketStatus(state, false, "Websocket da ngat. Dang thu ket noi lai...");
        for (const pending of state.pendingRequests.values()) {
            pending.reject(new Error("Websocket connection closed."));
        }
        state.pendingRequests.clear();
        window.setTimeout(connectSocket, 1200);
    });

    socket.addEventListener("error", () => {
        setSocketStatus(state, false, "Websocket gap loi");
    });
}

async function loadConversation(conversationId) {
    if (!conversationId || conversationId === state.conversationId) {
        return;
    }

    state.loadingConversationId = conversationId;
    renderRecentList(state);

    let conversation;
    try {
        const response = await sendSocketRequest(state, "load_conversation", { conversation_id: conversationId });
        conversation = response.conversation || null;
    } catch {
        conversation = await fetchConversationDetail(conversationId);
    } finally {
        state.loadingConversationId = "";
    }

    if (!conversation || !conversation.id) {
        renderRecentList(state);
        throw new Error("Khong nap duoc hoi thoai.");
    }

    state.conversationId = conversation.id;
    state.messages = Array.isArray(conversation.messages) ? conversation.messages : [];
    state.currentConversation = conversation;
    state.latestEvaluation = conversation.latest_agent_result || null;
    state.latestAdvisorContext = conversation.latest_advisor_context || null;
    upsertConversationSummary(conversation);
    renderMessages(state);
    renderInsights(state);
    renderRecentList(state);
}

async function sendHubMessage(message) {
    sendButton.disabled = true;
    try {
        const payload = await sendSocketRequest(state, "chat", {
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
        renderMessages(state);
        renderInsights(state);
        renderRecentList(state);
    } finally {
        sendButton.disabled = !state.socketReady;
    }
}

function startNewConversation() {
    state.conversationId = createConversationId();
    state.messages = [];
    state.currentConversation = null;
    state.latestEvaluation = null;
    state.latestAdvisorContext = null;
    state.selectedEvaluationCriteria = [];
    evaluatorInput.value = "";
    messageInput.value = "";
    messageInput.dispatchEvent(new Event("input"));
    messageInput.focus();
    renderAll();
}

async function runEvaluatorRequest() {
    if (!state.messages.length) {
        throw new Error("Chua co hoi thoai de danh gia.");
    }

    evaluatorButton.disabled = true;
    try {
        const payload = await sendSocketRequest(state, "evaluate", {
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
        renderMessages(state);
        renderInsights(state);
        renderRecentList(state);
    } finally {
        evaluatorButton.disabled = !state.socketReady;
    }
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

    renderEvaluatorCriteria(state);
    if (state.messages.length) {
        runEvaluatorRequest().catch((error) => {
            pushLocalError(error.message);
        });
    }
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

recentListEl.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-conversation-id]");
    if (!button || !recentListEl.contains(button)) {
        return;
    }

    try {
        await loadConversation(button.getAttribute("data-conversation-id") || "");
    } catch (error) {
        pushLocalError(error.message);
    }
});

criteriaDockEl.addEventListener("click", (event) => {
    const button = event.target.closest("[data-open-criterion]");
    if (!button || !criteriaDockEl.contains(button)) {
        return;
    }
    openCriterionPage(button.getAttribute("data-open-criterion") || "");
});

insightCriteriaEl.addEventListener("click", (event) => {
    const openButton = event.target.closest("[data-open-criterion]");
    if (openButton && insightCriteriaEl.contains(openButton)) {
        openCriterionPage(openButton.getAttribute("data-open-criterion") || "");
        return;
    }

    const fillButton = event.target.closest("[data-fill-criterion]");
    if (fillButton && insightCriteriaEl.contains(fillButton)) {
        fillCriterionPrompt(fillButton.getAttribute("data-fill-criterion") || "");
    }
});

evaluatorCriteriaEl.addEventListener("click", (event) => {
    const button = event.target.closest("[data-evaluator-criterion]");
    if (!button || !evaluatorCriteriaEl.contains(button)) {
        return;
    }
    toggleEvaluationCriterion(button.getAttribute("data-evaluator-criterion") || "");
});

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

renderMessages(state);
renderInsights(state);
renderRecentList(state);
renderCriteriaDock();
renderEvaluatorCriteria(state);
loadConfig().catch(() => {
    modelBadge.textContent = "Khong doc duoc Gemini config";
});
connectSocket();
