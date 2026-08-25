let dashboardData = null;

async function loadDashboard() {
    try {
        const response = await fetch("./data/latest.json?v=" + Date.now());

        if (!response.ok) {
            throw new Error("Cannot load latest.json");
        }

        dashboardData = await response.json();

        renderDashboard(dashboardData);

    } catch (err) {
        console.error(err);

        document.getElementById("updatedAt").textContent =
            "Unable to load dashboard data";

        document.getElementById("regimeLabel").textContent =
            "❌ DATA ERROR";
    }
}

function renderDashboard(data) {

    const overall = data.overall || {};

    document.getElementById("updatedAt").textContent =
        `Updated ${data.updated_at || "-"}`;

    document.getElementById("dataThrough").textContent =
        `Market data through ${data.data_through || "-"}`;

    const regime = document.getElementById("regimeLabel");
    regime.textContent = `${overall.emoji || "🟡"} ${overall.label || "WAITING"}`;
    regime.className = `regime-label ${overall.class || "yellow"}`;

    document.getElementById("score").textContent =
        `Score ${overall.score ?? 50}/100`;

    const action = document.getElementById("recommendedAction");
    action.textContent = overall.action || "Waiting";
    action.className = `recommended-action ${overall.class || "yellow"}`;

    document.getElementById("regimeReason").textContent =
        overall.reason || "";

    renderIndicatorsSafe(data);
    renderSnapshotSafe(data);
    renderDetailsSafe(data);

    document.getElementById("actionHeadline").innerHTML =
        `<span class="${overall.class || "yellow"}">${overall.emoji || "🟡"} ${overall.action || "Waiting"}</span>`;

    document.getElementById("actionExplanation").textContent =
        overall.reason || "";

    document.getElementById("sources").textContent =
        data.sources || "";
}

function renderIndicatorsSafe(data) {

    const grid = document.getElementById("indicatorGrid");
    grid.innerHTML = "";

    const indicators = data.indicators || [];

    indicators.forEach((item) => {

        const card = document.createElement("div");
        card.className = "indicator-card";

        card.innerHTML = `
            <div class="indicator-title">${item.name}</div>
            <div class="indicator-status ${item.class}">${item.emoji} ${item.status}</div>
            <div class="indicator-value">${item.value}</div>
            <div class="indicator-detail">${item.detail}</div>
        `;

        grid.appendChild(card);
    });
}

function renderSnapshotSafe(data) {

    const grid = document.getElementById("marketSnapshot");
    grid.innerHTML = "";

    (data.snapshot || []).forEach(item => {

        const box = document.createElement("div");
        box.className = "snapshot-item";

        box.innerHTML = `
            <span class="snapshot-value">${item.value}</span>
            <span class="snapshot-label">${item.name}</span>
        `;

        grid.appendChild(box);
    });
}

function renderDetailsSafe(data) {

    document.getElementById("valuationDetails").innerHTML =
        data.details?.valuation || "<p>No valuation data.</p>";

    document.getElementById("riskDetails").innerHTML =
        data.details?.risk || "<p>No risk data.</p>";

    document.getElementById("weeklyDetails").innerHTML =
        `<ul>${(data.what_matters || []).map(x => `<li>${x}</li>`).join("")}</ul>`;
}

document.getElementById("whyScoreButton").onclick = () => {

    if (!dashboardData) return;

    const rows = Object.entries(dashboardData.overall.breakdown || {})
        .map(([k, v]) => `<div class="legend-item"><strong>${k}</strong><br>${v}</div>`)
        .join("");

    openModal(`
        <h2>Why this score?</h2>
        <div class="legend-grid">${rows}</div>
    `);
};

document.addEventListener("DOMContentLoaded", loadDashboard);
