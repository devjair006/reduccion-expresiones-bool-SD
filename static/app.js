(function () {
    const expressionInput = document.getElementById("expression");
    const minInput = document.getElementById("min_variables");
    const maxInput = document.getElementById("max_variables");
    const showTraceInput = document.getElementById("show_trace");
    const checkEquivalenceInput = document.getElementById("check_equivalence");
    const demoButton = document.getElementById("btn-load-demo");
    const exampleButtons = document.querySelectorAll(".example-item");
    const historyButtons = document.querySelectorAll(".history-item");
    const copyButton = document.getElementById("copy-result");
    const guideToggle = document.getElementById("guide-toggle");
    const guideBody = document.getElementById("guide-body");

    if (guideToggle && guideBody) {
        guideToggle.addEventListener("click", () => {
            const isOpen = guideBody.classList.toggle("open");
            guideToggle.setAttribute("aria-expanded", isOpen);
        });
    }

    document.querySelectorAll(".mini-nav a").forEach((link) => {
        link.addEventListener("click", (e) => {
            const targetId = link.getAttribute("href")?.replace("#", "");
            if (!targetId) return;

            const target = document.getElementById(targetId);
            if (!target) return;

            const card = target.closest(".card-main, .card-dark") || target;
            card.classList.remove("nav-flash");
            void card.offsetWidth;
            card.classList.add("nav-flash");

            card.addEventListener("animationend", () => {
                card.classList.remove("nav-flash");
            }, { once: true });
        });
    });

    const setFormValues = (expression, minValue, maxValue, equivalence) => {
        if (!expressionInput) {
            return;
        }

        expressionInput.value = expression || "";

        if (minInput && minValue) {
            minInput.value = minValue;
        }

        if (maxInput && maxValue) {
            maxInput.value = maxValue;
        }

        if (checkEquivalenceInput && equivalence) {
            checkEquivalenceInput.checked = equivalence === "on";
        }

        if (showTraceInput && !showTraceInput.checked) {
            showTraceInput.checked = true;
        }

        expressionInput.focus();
        expressionInput.selectionStart = expressionInput.value.length;
        expressionInput.selectionEnd = expressionInput.value.length;
        expressionInput.scrollIntoView({ behavior: "smooth", block: "center" });
    };

    exampleButtons.forEach((button) => {
        button.addEventListener("click", () => {
            setFormValues(button.dataset.expression, button.dataset.min, button.dataset.max);
        });
    });

    historyButtons.forEach((button) => {
        button.addEventListener("click", () => {
            setFormValues(
                button.dataset.expression,
                button.dataset.min,
                button.dataset.max,
                button.dataset.equivalence
            );
        });
    });

    if (demoButton) {
        demoButton.addEventListener("click", () => {
            setFormValues("F = A.B.C + A.B.C' + D.E.F + D.E.F'", "6", "10", "off");
        });
    }

    if (copyButton) {
        copyButton.addEventListener("click", async () => {
            const value = copyButton.dataset.result || "";
            if (!value) {
                return;
            }

            const previous = copyButton.textContent;
            try {
                await navigator.clipboard.writeText(value);
                copyButton.textContent = "Copiado";
            } catch (error) {
                copyButton.textContent = "No se pudo copiar";
            }

            setTimeout(() => {
                copyButton.textContent = previous;
            }, 1400);
        });
    }
})();
