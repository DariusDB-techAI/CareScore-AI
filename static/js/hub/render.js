import {
    activeConversationLabelEl,
    criteriaDockEl,
    evaluatorCriteriaEl,
    evaluatorPlanMetaEl,
    insightCriteriaEl,
    messagesEl,
    recentCountLabelEl,
    recentListEl,
} from "./dom.js";
import { criteriaConfig } from "./bootstrap.js";
import { escapeHtml, formatTime, getConversationLabel } from "./utils.js";

export function renderEmptyState() {
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

export function renderMessages(state) {
    if (!state.messages.length) {
        renderEmptyState();
        return;
    }

    messagesEl.innerHTML = state.messages.map((message) => {
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
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

export function renderRecentList(state) {
    recentCountLabelEl.textContent = `${state.conversations.length} thread${state.conversations.length === 1 ? "" : "s"}`;
    activeConversationLabelEl.textContent = getConversationLabel(state.currentConversation);

    if (!state.conversations.length) {
        recentListEl.innerHTML = `<div class="recent-empty">Chua co hoi thoai nao.</div>`;
        return;
    }

    recentListEl.innerHTML = state.conversations.map((conversation) => `
        <button
            class="recent-item ${conversation.id === state.conversationId ? "is-active" : ""} ${conversation.id === state.loadingConversationId ? "is-loading" : ""}"
            type="button"
            data-conversation-id="${escapeHtml(conversation.id)}"
        >
            <strong>${escapeHtml(conversation.title || "Cuoc hoi thoai moi")}</strong>
            <span>${escapeHtml(conversation.preview || "Chua co preview")}</span>
            <small>${escapeHtml(formatTime(conversation.updated_at))}</small>
        </button>
    `).join("");
}

export function renderInsights(state) {
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
        evaluatorPlanMetaEl.textContent = `Routed: ${routed} | Source: ${orchestrator.source || "runtime"}`;
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
}

export function renderCriteriaDock() {
    criteriaDockEl.innerHTML = criteriaConfig.map((criterion, index) => `
        <button class="criteria-option" type="button" data-open-criterion="${escapeHtml(criterion.id)}">
            <span class="criteria-option__index">0${index + 1}</span>
            <strong>${escapeHtml(criterion.label)}</strong>
        </button>
    `).join("");
}

export function renderEvaluatorCriteria(state) {
    evaluatorCriteriaEl.innerHTML = criteriaConfig.map((criterion) => `
        <button
            class="evaluator-chip ${state.selectedEvaluationCriteria.includes(criterion.id) ? "is-active" : ""}"
            type="button"
            data-evaluator-criterion="${escapeHtml(criterion.id)}"
        >
            ${escapeHtml(criterion.label)}
        </button>
    `).join("");
}
