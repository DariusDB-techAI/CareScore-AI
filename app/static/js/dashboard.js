let barChart;
let radarChart;

function average(values) {
    if (!values.length) return 0;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function buildSummary(conversations) {
    const labels = Object.keys(window.APP_CRITERIA);
    const criterionAverages = labels.map((criterion) => {
        const scores = conversations
            .map((conversation) => conversation.evaluations?.[criterion]?.score)
            .filter((score) => typeof score === "number");
        return Number(average(scores).toFixed(2));
    });

    const totalEvaluations = conversations.reduce(
        (sum, conversation) => sum + Object.keys(conversation.evaluations || {}).length,
        0
    );

    const flatScores = conversations.flatMap((conversation) =>
        Object.values(conversation.evaluations || {}).map((item) => item.score)
    );

    return {
        criterionAverages,
        totalEvaluations,
        overallAverage: average(flatScores).toFixed(1),
    };
}

function renderKpis(conversations, summary) {
    document.getElementById("kpiTotal").textContent = conversations.length;
    document.getElementById("kpiEvaluations").textContent = summary.totalEvaluations;
    document.getElementById("kpiAverage").textContent = summary.overallAverage;
}

function renderCharts(summary) {
    const labels = Object.values(window.APP_CRITERIA).map((item) => item.label);
    const chartColor = "rgba(157, 223, 115, 0.92)";
    const chartFill = "rgba(157, 223, 115, 0.18)";

    if (barChart) barChart.destroy();
    if (radarChart) radarChart.destroy();

    barChart = new Chart(document.getElementById("barChart"), {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Diem trung binh",
                data: summary.criterionAverages,
                borderRadius: 16,
                backgroundColor: ["#58d9c2", "#ffa45f", "#64b5ff", "#ff6f61", "#7ad66b"],
            }],
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    min: 0,
                    max: 5,
                    ticks: { color: "#d8e1ec" },
                    grid: { color: "rgba(255,255,255,0.08)" },
                },
                x: {
                    ticks: { color: "#d8e1ec" },
                    grid: { display: false },
                },
            },
            plugins: {
                legend: { display: false },
            },
        },
    });

    radarChart = new Chart(document.getElementById("radarChart"), {
        type: "radar",
        data: {
            labels,
            datasets: [{
                label: "Tong quan chat luong",
                data: summary.criterionAverages,
                borderColor: chartColor,
                backgroundColor: chartFill,
                pointBackgroundColor: "#ffffff",
            }],
        },
        options: {
            responsive: true,
            scales: {
                r: {
                    min: 0,
                    max: 5,
                    angleLines: { color: "rgba(255,255,255,0.12)" },
                    grid: { color: "rgba(255,255,255,0.12)" },
                    pointLabels: { color: "#d8e1ec" },
                    ticks: {
                        color: "#d8e1ec",
                        backdropColor: "transparent",
                    },
                },
            },
            plugins: {
                legend: {
                    labels: { color: "#d8e1ec" },
                },
            },
        },
    });
}

function renderConversationSummary(conversations) {
    const container = document.getElementById("conversationSummary");
    if (!conversations.length) {
        container.innerHTML = `<div class="empty-state"><p>Chua co du lieu hoi thoai de tong hop.</p></div>`;
        return;
    }

    container.innerHTML = conversations.map((conversation) => {
        const tags = Object.values(conversation.evaluations || {})
            .map((item) => `<span class="summary-tag">${item.label}: ${item.score}/5</span>`)
            .join("");

        return `
            <article class="summary-row">
                <div>
                    <strong>${conversation.title}</strong>
                    <p>${conversation.messages.length} tin nhan · ${new Date(conversation.created_at).toLocaleString("vi-VN")}</p>
                </div>
                <div class="summary-tags">${tags || '<span class="summary-tag">Chua co danh gia</span>'}</div>
            </article>
        `;
    }).join("");
}

async function initDashboard() {
    const response = await fetch("/api/conversations");
    const conversations = await response.json();
    const summary = buildSummary(conversations);
    renderKpis(conversations, summary);
    renderCharts(summary);
    renderConversationSummary(conversations);
}

initDashboard();
