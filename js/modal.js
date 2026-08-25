/* ============================================================
   MODAL SYSTEM
============================================================ */

function openModal(html) {

    const modal =
        document.getElementById("indicatorModal");

    const body =
        document.getElementById("modalBody");

    body.innerHTML = html;

    modal.classList.add("open");
}


function closeModal() {

    const modal =
        document.getElementById("indicatorModal");

    modal.classList.remove("open");
}


document
    .getElementById("closeModal")
    .addEventListener(
        "click",
        closeModal
    );


document
    .getElementById("indicatorModal")
    .addEventListener(
        "click",
        function(event) {

            if (
                event.target === this
            ) {

                closeModal();

            }

        }
    );


document.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Escape") {

            closeModal();

        }

    }
);