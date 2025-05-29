document.addEventListener("DOMContentLoaded", function () {
    console.log("Contact page loaded.");

    // Copy phone number to clipboard
    document.querySelectorAll(".copy-number").forEach(function (phone) {
        phone.addEventListener("click", function () {
            const number = phone.innerText;
            navigator.clipboard.writeText(number).then(() => {
                alert("Phone number copied: " + number);
            });
        });
    });

    // Alert when clicking email
    document.querySelectorAll(".contact-email").forEach(function (email) {
        email.addEventListener("click", function () {
            alert("Opening email: " + email.innerText);
        });
    });
});
