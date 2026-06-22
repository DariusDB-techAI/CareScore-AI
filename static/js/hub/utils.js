export function createConversationId() {
    return `conversation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

export function formatTime(value) {
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

export function buildTranscriptFromMessages(messages) {
    return (Array.isArray(messages) ? messages : [])
        .filter((message) => (message.message_kind || "chat") === "chat")
        .map((message) => {
            const role = message.role === "user" ? "Khach hang" : "Nhan vien";
            const content = String(message.content || "").trim();
            return content ? `${role}: ${content}` : "";
        })
        .filter(Boolean)
        .join("\n");
}

export function getConversationLabel(conversation) {
    if (!conversation || !conversation.id) {
        return "Dang mo thread moi";
    }
    return conversation.title || "Dang mo hoi thoai";
}
