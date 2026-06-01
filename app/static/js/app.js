const socket = window.io ? io() : null;

const state = {
    activeConversationId: null,
    conversations: [],
};

const conversationList = document.getElementById("conversationList");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const newConversationBtn = document.getElementById("newConversationBtn");
const themeButtons = document.querySelectorAll(".theme-btn");
const conversationCount = document.getElementById("conversationCount");
const evaluationCount = document.getElementById("evaluationCount");
const messageCount = document.getElementById("messageCount");
const activeConversationTitle = document.getElementById("activeConversationTitle");
const transportStatus = document.getElementById("transportStatus");
const activeThemeLabel = document.getElementById("activeThemeLabel");

const themeNames = {
    aurora: "Aurora",
    sunset: "Sunset",
    ocean: "Ocean",
    ember: "Ember",
    forest: "Forest",
};

if (transportStatus) {
    transportStatus.textContent = socket ? "WebSocket Live" : "HTTP Fallback";
}

async function fetchChatbotConfig() {
    try {
        const response = await fetch("/api/chatbot-config");
        if (!response.ok || !transportStatus) {
            return;
        }
        const config = await response.json();

        if (config.provider === "openai") {
            transportStatus.textContent = `OpenAI � ${config.openai_model}`;
            return;
        }

        if (config.provider === "ollama") {
            transportStatus.textContent = `Ollama � ${config.ollama_model}`;
            return;
        }

        transportStatus.textContent = "Mock Chatbot";
    } catch (error) {
        console.warn("Could not load chatbot config", error);
    }
}

async function fetchConversations() {
    const response = await fetch("/api/conversations");
    state.conversations = await response.json();
    if (!state.activeConversationId && state.conversations.length) {
        state.activeConversationId = state.conversations[0].id;
    }
    updateOverviewStats();
    renderConversationList();
    renderActiveConversation();
}

function createConversationLocally() {
    state.activeConversationId = null;
    updateOverviewStats();
    renderConversationList();
    renderMessages([]);
}

function updateOverviewStats() {
    if (conversationCount) {
        conversationCount.textContent = state.conversations.length;
    }

    if (evaluationCount) {
        const total = state.conversations.reduce(
            (sum, conversation) => sum + Object.keys(conversation.evaluations || {}).length,
            0
        );
        evaluationCount.textContent = total;
    }
}

function renderConversationList() {
    conversationList.innerHTML = "";
    if (!state.conversations.length) {
        conversationList.innerHTML = `<div class="empty-state"><p>Chua co hoi thoai nao.</p></div>`;
        return;
    }

    state.conversations.forEach((conversation) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = `conversation-item ${conversation.id === state.activeConversationId ? "active" : ""}`;
        item.innerHTML = `
            <strong>${conversation.title}</strong>
            <p>${conversation.messages.length} tin nhan � ${Object.keys(conversation.evaluations || {}).length} danh gia</p>
        `;
        item.addEventListener("click", () => {
            state.activeConversationId = conversation.id;
            renderConversationList();
            renderActiveConversation();
        });
        conversationList.appendChild(item);
    });
}

function renderMessages(messages) {
    if (!messages.length) {
        chatMessages.innerHTML = `
            <div class="empty-state">
                <h3>Bat dau mot phien chat</h3>
                <p>Nhap noi dung khach hang hoac nhan vien de tao transcript. Sau do chay cac model ben phai de danh gia chat luong hoi thoai.</p>
            </div>
        `;
        if (messageCount) {
            messageCount.textContent = "0 tin nhan";
        }
        return;
    }

    chatMessages.innerHTML = "";
    messages.forEach((message) => {
        const row = document.createElement("section");
        row.className = `message-row ${message.role === "assistant" ? "assistant-row" : "user-row"}`;

        const node = document.createElement("article");
        node.className = `message ${message.role}`;
        node.innerHTML = `
            <div class="message-body">${message.content}</div>
            <span class="message-meta">${message.role} � ${message.timestamp}</span>
        `;

        row.appendChild(node);
        chatMessages.appendChild(row);
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (messageCount) {
        messageCount.textContent = `${messages.length} tin nhan`;
    }
}

function renderActiveConversation() {
    const conversation = state.conversations.find((item) => item.id === state.activeConversationId);
    if (activeConversationTitle) {
        activeConversationTitle.textContent = conversation ? conversation.title : "Phien danh gia moi";
    }
    renderMessages(conversation ? conversation.messages : []);
}

function setTheme(theme) {
    document.body.dataset.theme = theme;
    if (activeThemeLabel) {
        activeThemeLabel.textContent = themeNames[theme] || theme;
    }
}

chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (!message) {
        return;
    }

    if (socket) {
        socket.emit("send_message", {
            conversation_id: state.activeConversationId,
            message,
        });
    } else {
        const response = await fetch("/api/message", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                conversation_id: state.activeConversationId,
                message,
            }),
        });
        const conversation = await response.json();
        if (response.ok) {
            upsertConversation(conversation);
        }
    }

    messageInput.value = "";
    messageInput.style.height = "60px";
});

messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 180)}px`;
});

messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});

newConversationBtn.addEventListener("click", createConversationLocally);

function upsertConversation(conversation) {
    const index = state.conversations.findIndex((item) => item.id === conversation.id);
    if (index === -1) {
        state.conversations.unshift(conversation);
    } else {
        state.conversations[index] = conversation;
    }

    if (!state.activeConversationId) {
        state.activeConversationId = conversation.id;
    }
    updateOverviewStats();
    renderConversationList();
    if (state.activeConversationId === conversation.id) {
        renderActiveConversation();
    }
}

if (socket) {
    socket.on("message", ({ conversation_id, message }) => {
        let conversation = state.conversations.find((item) => item.id === conversation_id);
        if (!conversation) {
            conversation = {
                id: conversation_id,
                title: "Cuoc hoi thoai moi",
                messages: [],
                evaluations: {},
            };
            state.conversations.unshift(conversation);
        }

        conversation.messages.push(message);
        if (!state.activeConversationId) {
            state.activeConversationId = conversation_id;
        }
        updateOverviewStats();
        renderConversationList();
        if (state.activeConversationId === conversation_id) {
            renderActiveConversation();
        }
    });

    socket.on("conversation_updated", (conversation) => {
        upsertConversation(conversation);
    });
} else {
    console.warn("Socket.IO client not loaded. Using HTTP fallback for chat.");
}

themeButtons.forEach((button) => {
    button.addEventListener("click", async () => {
        const criterion = button.dataset.criterion;
        const theme = button.dataset.theme;
        setTheme(theme);

        const conversationId = state.activeConversationId;
        const resultBox = document.getElementById(`result-${criterion}`);

        if (!conversationId) {
            resultBox.innerHTML = `
                <div class="result-empty">
                    <span class="result-score">--</span>
                    <p>Can co hoi thoai truoc khi chay danh gia.</p>
                </div>
            `;
            return;
        }

        resultBox.innerHTML = `
            <div class="result-empty">
                <span class="result-score">...</span>
                <p>Dang chay model va tong hop ket qua.</p>
            </div>
        `;

        const response = await fetch(`/api/evaluate/${conversationId}/${criterion}`, { method: "POST" });
        const result = await response.json();

        if (!response.ok) {
            resultBox.innerHTML = `
                <div class="result-empty">
                    <span class="result-score">ERR</span>
                    <p>${result.error || "Khong the danh gia."}</p>
                </div>
            `;
            return;
        }

        resultBox.innerHTML = `
            <div class="result-content">
                <div class="result-topline">
                    <span class="result-score">${result.score}/5</span>
                    <span class="theme-tag">${result.label}</span>
                </div>
                <p class="result-summary">${result.summary}</p>
                <div class="result-footer">
                    <span>Confidence: ${Math.round(result.confidence * 100)}%</span>
                    <span>${result.model_hint}</span>
                </div>
            </div>
        `;

        const activeConversation = state.conversations.find((item) => item.id === conversationId);
        if (activeConversation) {
            activeConversation.evaluations[criterion] = result;
            updateOverviewStats();
            renderConversationList();
        }
    });
});

setTheme(document.body.dataset.theme || "aurora");
fetchChatbotConfig();
fetchConversations();
