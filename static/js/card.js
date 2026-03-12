document.addEventListener("DOMContentLoaded", () => {
    const cards = document.querySelectorAll(".member-card");

    cards.forEach((card) => {
        card.addEventListener("click", (event) => {
            if (event.target.closest("a")) return;

            const isActive = card.classList.contains("active");

            cards.forEach((item) => item.classList.remove("active"));

            if (!isActive) {
                card.classList.add("active");
            }
        });
    });
});