document.addEventListener("DOMContentLoaded", () => {
    const CLAMP_LINES = 3;

    function updateToggle(row) {
        const value = row.querySelector(".prov-value");
        const toggle = row.querySelector(".prov-toggle");
        const lineHeight = parseFloat(getComputedStyle(value).lineHeight);
        const overflows = value.scrollHeight > lineHeight * CLAMP_LINES + 1;
        toggle.classList.toggle("d-none", !overflows);
        toggle.textContent = value.classList.contains("prov-clamped") ? "Show more" : "Show less";
    }

    function showSource(row, source) {
        row.querySelectorAll(".prov-text").forEach(text => {
            text.classList.toggle("d-none", text.dataset.source !== source);
        });
        row.querySelectorAll("button.prov-pill").forEach(pill => {
            pill.setAttribute("aria-pressed", String(pill.dataset.source === source));
        });
        updateToggle(row);
    }

    document.querySelectorAll(".provenance-modal").forEach(modal => {
        const rows = modal.querySelectorAll(".prov-row");

        rows.forEach(row => {
            row.querySelector(".prov-toggle").addEventListener("click", () => {
                row.querySelector(".prov-value").classList.toggle("prov-clamped");
                updateToggle(row);
            });

            row.querySelectorAll("button.prov-pill").forEach(pill => {
                pill.addEventListener("click", () => {
                    const active = pill.getAttribute("aria-pressed") === "true";
                    showSource(row, active ? "" : pill.dataset.source);
                });
            });
        });

        modal.addEventListener("shown.bs.modal", () => rows.forEach(updateToggle));
    });
});
