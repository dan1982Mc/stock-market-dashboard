/* ============================================================
   INDICATOR PRESENTATION
============================================================ */

function statusClass(status) {

    const map = {

        "BULLISH": "green",
        "HEALTHY": "green",
        "ATTRACTIVE": "green",
        "NORMAL": "green",

        "NEUTRAL": "yellow",
        "MIXED": "yellow",
        "ELEVATED": "yellow",
        "OPTIMISTIC": "yellow",

        "EXPENSIVE": "orange",
        "RESTRICTIVE": "orange",
        "CAUTION": "orange",

        "BEARISH": "red",
        "WEAK": "red",
        "STRESS": "red",
        "PANIC": "red",
        "EXTREME": "red",
        "FEARFUL": "red"
    };

    return map[status] || "yellow";
}


function renderIndicators(data) {

    const container =
        document.getElementById(
            "indicatorGrid"
        );

    container.innerHTML = "";

    data.indicators.forEach(
        (indicator, index) => {

            const card =
                document.createElement("div");

            card.className =
                "indicator-card";

            card.innerHTML = `

                <button
                    class="info-button"
                    data-index="${index}">
                    i
                </button>

                <div class="indicator-title">
                    ${indicator.name}
                </div>

                <div class="
                    indicator-status
                    ${statusClass(indicator.status)}
                ">
                    ${indicator.emoji}
                    ${indicator.status}
                </div>

                <div class="indicator-value">
                    ${indicator.value}
                </div>

                <div class="indicator-detail">
                    ${indicator.detail}
                </div>

                <div class="indicator-detail">
                    Data: ${indicator.as_of}
                </div>
            `;

            container.appendChild(card);
        }
    );


    container
        .querySelectorAll(".info-button")
        .forEach(button => {

            button.addEventListener(
                "click",
                function() {

                    const index =
                        Number(
                            this.dataset.index
                        );

                    showIndicatorExplanation(
                        data.indicators[index]
                    );

                }
            );

        });
}


function showIndicatorExplanation(indicator) {

    const explanation =
        indicator.explanation;

    const legend =
        explanation.legend
            .map(
                item =>
                    `<div class="legend-item">${item}</div>`
            )
            .join("");

    openModal(`

        <h2>
            ${indicator.name}
        </h2>

        <p>

            <strong
                class="${statusClass(indicator.status)}">

                ${indicator.emoji}
                ${indicator.status}

            </strong>

            — ${indicator.value}

        </p>


        <h3>
            What does it measure?
        </h3>

        <p>
            ${explanation.what}
        </p>


        <h3>
            How should I read it?
        </h3>

        <div class="legend-grid">

            ${legend}

        </div>


        <h3>
            Why does it matter?
        </h3>

        <p>
            ${explanation.why}
        </p>


        <p class="muted">

            Source:
            ${explanation.source}

            <br>

            Last update:
            ${indicator.as_of}

        </p>

    `);
}