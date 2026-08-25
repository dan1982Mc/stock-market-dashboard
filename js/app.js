let dashboardData = null;


/* =========================================================
   LOAD DATA
   ========================================================= */

async function loadDashboard() {

    try {

        const response = await fetch(
            "./data/latest.json?v=" + Date.now()
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        dashboardData = await response.json();

        renderDashboard(dashboardData);

    }

    catch (error) {

        console.error(
            "Dashboard data error:",
            error
        );

        showDataError();
    }
}


/* =========================================================
   MAIN RENDER
   ========================================================= */

function renderDashboard(data) {

    const overall =
        data.overall || {};

    /* ---------------------------------------------
       Header
    --------------------------------------------- */

    const updated =
        document.getElementById("updatedAt");

    if (updated) {

        updated.textContent =
            `Updated ${data.updated_at || "-"}`;
    }


    const dataThrough =
        document.getElementById("dataThrough");

    if (dataThrough) {

        dataThrough.textContent =
            `Market data through ${
                data.data_through || "-"
            }`;
    }


    /* ---------------------------------------------
       Mode
    --------------------------------------------- */

    updateModeBadge(data);


    /* ---------------------------------------------
       Regime
    --------------------------------------------- */

    const regime =
        document.getElementById("regimeLabel");

    if (regime) {

        regime.textContent =
            `${overall.emoji || "🟡"} ${
                overall.label || "WAITING"
            }`;

        regime.className =
            `regime-label ${
                overall.class || "yellow"
            }`;
    }


    /* ---------------------------------------------
       Score
    --------------------------------------------- */

    const score =
        document.getElementById("score");

    if (score) {

        score.textContent =
            `Score ${
                overall.score ?? "—"
            }/100`;
    }


    /* ---------------------------------------------
       Action
    --------------------------------------------- */

    const action =
        document.getElementById(
            "recommendedAction"
        );

    if (action) {

        action.textContent =
            overall.action || "Waiting";

        action.className =
            `recommended-action ${
                overall.class || "yellow"
            }`;
    }


    const reason =
        document.getElementById(
            "regimeReason"
        );

    if (reason) {

        reason.textContent =
            overall.reason || "";
    }


    /* ---------------------------------------------
       Sections
    --------------------------------------------- */

    renderIndicators(data);

    renderSnapshot(data);

    renderDetails(data);

    renderAction(data);

    renderSources(data);
}


/* =========================================================
   LIVE / DEMO / STALE BADGE
   ========================================================= */

function updateModeBadge(data) {

    let badge =
        document.getElementById(
            "dataModeBadge"
        );

    if (!badge) {

        badge =
            document.createElement("div");

        badge.id =
            "dataModeBadge";

        badge.className =
            "data-mode-badge";

        const header =
            document.querySelector("header");

        if (header) {

            header.appendChild(badge);

        } else {

            document.body.prepend(badge);
        }
    }


    const mode =
        data.mode || "DEMO";


    if (mode === "LIVE") {

        badge.textContent =
            "🟢 LIVE DATA";

        badge.className =
            "data-mode-badge live";

        return;
    }


    if (mode === "DEMO") {

        badge.textContent =
            "🟡 DEMO DATA";

        badge.className =
            "data-mode-badge demo";

        return;
    }


    badge.textContent =
        "🔴 STALE DATA";

    badge.className =
        "data-mode-badge stale";
}


/* =========================================================
   INDICATORS
   ========================================================= */

function renderIndicators(data) {

    const grid =
        document.getElementById(
            "indicatorGrid"
        );

    if (!grid) return;

    grid.innerHTML = "";


    const indicators =
        data.indicators || [];


    if (indicators.length === 0) {

        grid.innerHTML = `
            <div class="empty-state">
                No indicator data available.
            </div>
        `;

        return;
    }


    indicators.forEach(item => {

        const card =
            document.createElement("div");

        card.className =
            "indicator-card";


        card.innerHTML = `

            <div class="indicator-title">
                ${item.name || ""}
            </div>

            <div class="
                indicator-status
                ${item.class || "gray"}
            ">
                ${item.emoji || "⚪"}
                ${item.status || "NO DATA"}
            </div>

            <div class="indicator-value">
                ${item.value ?? "—"}
            </div>

            <div class="indicator-detail">
                ${item.detail || ""}
            </div>

        `;


        grid.appendChild(card);

    });
}


/* =========================================================
   SNAPSHOT
   ========================================================= */

function renderSnapshot(data) {

    const grid =
        document.getElementById(
            "marketSnapshot"
        );

    if (!grid) return;

    grid.innerHTML = "";


    (data.snapshot || [])
        .forEach(item => {

            const box =
                document.createElement("div");

            box.className =
                "snapshot-item";


            box.innerHTML = `

                <span class="snapshot-value">
                    ${item.value ?? "—"}
                </span>

                <span class="snapshot-label">
                    ${item.name || ""}
                </span>

            `;


            grid.appendChild(box);

        });
}


/* =========================================================
   DETAILS
   ========================================================= */

function renderDetails(data) {

    const valuation =
        document.getElementById(
            "valuationDetails"
        );

    if (valuation) {

        valuation.innerHTML =
            data.details?.valuation ||
            "<p>No valuation data.</p>";
    }


    const risk =
        document.getElementById(
            "riskDetails"
        );

    if (risk) {

        risk.innerHTML =
            data.details?.risk ||
            "<p>No risk data.</p>";
    }


    const weekly =
        document.getElementById(
            "weeklyDetails"
        );

    if (weekly) {

        weekly.innerHTML = `

            <ul>

                ${(data.what_matters || [])
                    .map(
                        item =>
                            `<li>${item}</li>`
                    )
                    .join("")
                }

            </ul>

        `;
    }
}


/* =========================================================
   ACTION
   ========================================================= */

function renderAction(data) {

    const overall =
        data.overall || {};


    const headline =
        document.getElementById(
            "actionHeadline"
        );

    if (headline) {

        headline.innerHTML = `

            <span class="${
                overall.class || "yellow"
            }">

                ${overall.emoji || "🟡"}
                ${overall.action || "Waiting"}

            </span>
        `;
    }


    const explanation =
        document.getElementById(
            "actionExplanation"
        );

    if (explanation) {

        explanation.textContent =
            overall.reason || "";
    }
}


/* =========================================================
   SOURCES
   ========================================================= */

function renderSources(data) {

    const element =
        document.getElementById(
            "sources"
        );

    if (element) {

        element.textContent =
            data.sources || "";
    }
}


/* =========================================================
   ERROR
   ========================================================= */

function showDataError() {

    const regime =
        document.getElementById(
            "regimeLabel"
        );

    if (regime) {

        regime.textContent =
            "🔴 DATA ERROR";

        regime.className =
            "regime-label red";
    }


    const score =
        document.getElementById(
            "score"
        );

    if (score) {

        score.textContent =
            "Score —";
    }


    const action =
        document.getElementById(
            "recommendedAction"
        );

    if (action) {

        action.textContent =
            "DATA UNAVAILABLE";
    }


    updateModeBadge({
        mode: "STALE"
    });
}


/* =========================================================
   WHY SCORE
   ========================================================= */

function setupWhyScore() {

    const button =
        document.getElementById(
            "whyScoreButton"
        );

    if (!button) return;


    button.addEventListener(
        "click",
        () => {

            if (!dashboardData)
                return;


            const breakdown =
                dashboardData
                    .overall
                    ?.breakdown || {};


            const rows =
                Object.entries(
                    breakdown
                )
                .map(
                    ([key, value]) => `

                        <div class="
                            legend-item
                        ">

                            <strong>
                                ${key}
                            </strong>

                            <span>
                                ${value}
                            </span>

                        </div>
                    `
                )
                .join("");


            if (
                typeof openModal ===
                "function"
            ) {

                openModal(`

                    <h2>
                        Why this score?
                    </h2>

                    <div class="
                        legend-grid
                    ">

                        ${rows}

                    </div>

                `);
            }

        }
    );
}


/* =========================================================
   START
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadDashboard();

        setupWhyScore();

    }
);
