const criterionBootstrap = window.CRITERION_BOOTSTRAP || {};
const criterionConfig = criterionBootstrap.criterion || {};
const criterionTheme = criterionBootstrap.theme || {};
const criterionId = String(criterionConfig.id || "");
const draftStorageKey = criterionId ? `criterionDraft:${criterionId}` : "";

const inputEl = document.getElementById("criterionInput");
const evaluateButton = document.getElementById("evaluateButton");
const clearButton = document.getElementById("clearButton");
const useDraftButton = document.getElementById("useDraftButton");
const resultPanel = document.getElementById("resultPanel");
const statusMessage = document.getElementById("statusMessage");

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function toPercent(value) {
    return `${Math.round(Number(value || 0) * 100)}%`;
}

function setStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusMessage.classList.toggle("is-error", Boolean(isError));
}

function buildProbabilityRows(probabilities) {
    const entries = Object.entries(probabilities || {});
    if (!entries.length) {
        return "<p>Chua co probability detail cho transcript hien tai.</p>";
    }

    return `
        <div class="probability-table">
            ${entries.map(([label, score]) => `
                <div class="probability-row">
                    <div class="table-label">${escapeHtml(label)}</div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width:${Math.max(0, Math.min(100, Number(score || 0) * 100))}%"></div>
                    </div>
                    <strong>${escapeHtml(toPercent(score))}</strong>
                </div>
            `).join("")}
        </div>
    `;
}

function buildMetaRows(result) {
    const preprocess = result.preprocess || {};
    return `
        <div class="meta-list">
            <div class="meta-row">
                <span>Raw label</span>
                <strong>${escapeHtml(result.raw_label || "")}</strong>
            </div>
            <div class="meta-row">
                <span>Status</span>
                <strong>${escapeHtml(result.status || "")}</strong>
            </div>
            <div class="meta-row">
                <span>Notebook source</span>
                <strong>${escapeHtml(preprocess.notebook_source || result.model_hint || "")}</strong>
            </div>
            <div class="meta-row">
                <span>Line count</span>
                <strong>${escapeHtml(preprocess.line_count ?? 0)}</strong>
            </div>
        </div>
    `;
}

function renderEvaluation(result) {
    resultPanel.innerHTML = `
        <article class="result-card">
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-label">Score</div>
                    <div class="metric-value">${escapeHtml(result.score)}/5</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Confidence</div>
                    <div class="metric-value">${escapeHtml(toPercent(result.confidence))}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Criterion</div>
                    <div class="metric-value" style="font-size:24px;color:${escapeHtml(criterionTheme.ink || "#111")}">${escapeHtml(criterionConfig.label || criterionId)}</div>
                </div>
            </div>
        </article>
        <article class="result-card result-body">
            <section class="result-section">
                <h3>Tom tat dien giai</h3>
                <p>${escapeHtml(result.summary || "")}</p>
            </section>
            <section class="result-section">
                <h3>Probability</h3>
                ${buildProbabilityRows(result.probabilities || {})}
            </section>
            <section class="result-section">
                <h3>Model meta</h3>
                ${buildMetaRows(result)}
            </section>
        </article>
    `;
}

function getDraftText() {
    if (!draftStorageKey) {
        return "";
    }

    try {
        return localStorage.getItem(draftStorageKey) || "";
    } catch {
        return "";
    }
}

function setDraftText(value) {
    if (!draftStorageKey) {
        return;
    }

    try {
        if (value) {
            localStorage.setItem(draftStorageKey, value);
        } else {
            localStorage.removeItem(draftStorageKey);
        }
    } catch {
        // Ignore storage errors and continue with in-memory UX.
    }
}

async function evaluateCriterion() {
    const text = inputEl.value.trim();
    setDraftText(text);
    setStatus("Dang goi local model cho tieu chi nay...");
    evaluateButton.disabled = true;

    try {
        const response = await fetch(`/api/criterion/${encodeURIComponent(criterionId)}/evaluate`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ text }),
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Criterion evaluation failed.");
        }

        renderEvaluation(payload.evaluation || {});
        setStatus("Da cap nhat ket qua moi.");
    } catch (error) {
        setStatus(`Loi: ${error.message}`, true);
    } finally {
        evaluateButton.disabled = false;
    }
}

evaluateButton.addEventListener("click", () => {
    void evaluateCriterion();
});

clearButton.addEventListener("click", () => {
    inputEl.value = "";
    setDraftText("");
    resultPanel.innerHTML = `
        <article class="result-card result-card--empty">
            <h3>Da xoa transcript</h3>
            <p>Nhap noi dung moi roi bam evaluate de tao ket qua tiep theo.</p>
        </article>
    `;
    setStatus("Transcript da duoc xoa.");
    inputEl.focus();
});

useDraftButton.addEventListener("click", () => {
    const draft = getDraftText();
    if (!draft.trim()) {
        setStatus("Chua thay thread nao duoc day sang tu hub.");
        return;
    }

    inputEl.value = draft;
    setStatus("Da nap transcript tu hub.");
});

inputEl.addEventListener("input", () => {
    setDraftText(inputEl.value);
});

window.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        void evaluateCriterion();
    }
});

const initialDraft = getDraftText();
if (initialDraft.trim()) {
    inputEl.value = initialDraft;
    setStatus("Da tim thay transcript tu hub. Ban co the bam evaluate ngay.");
}
