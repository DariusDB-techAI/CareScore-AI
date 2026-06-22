import { connectionBadge, evaluatorButton, modelBadge, sendButton } from "./dom.js";
import { getWsPath } from "./bootstrap.js";

export function setSocketStatus(state, ready, label) {
    state.socketReady = ready;
    connectionBadge.textContent = label;
    connectionBadge.classList.toggle("is-live", ready);
    sendButton.disabled = !ready;
    evaluatorButton.disabled = !ready;
}

export function buildSocketUrl() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}${getWsPath()}`;
}

export function sendSocketRequest(state, type, payload) {
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

export async function fetchConversationDetail(conversationId) {
    const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(payload.error || "Khong nap duoc hoi thoai.");
    }
    return payload;
}

export async function loadConfig() {
    const response = await fetch("/api/config");
    const payload = await response.json();
    modelBadge.textContent = payload.configured
        ? `Gemini | ${payload.model}`
        : `Gemini chua cau hinh | ${payload.model}`;
}
