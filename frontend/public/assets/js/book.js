document.getElementById("appointment-form").addEventListener("submit", function (e) {
    e.preventDefault();

    const confirmation = document.getElementById("confirmation");
    confirmation.classList.remove("hidden");

    // Hide after 4 seconds
    setTimeout(() => {
        confirmation.classList.add("hidden");
    }, 4000);

    // Optionally, reset the form
    this.reset();
});
