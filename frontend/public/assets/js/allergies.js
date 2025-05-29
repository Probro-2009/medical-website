let slides = document.querySelectorAll(".slide");
let index = 0;

function showSlides() {
    slides.forEach(slide => slide.style.opacity = "0");
    slides[index].style.opacity = "1";
    index = (index + 1) % slides.length;
}

setInterval(showSlides, 5000); // Change image every 5 seconds
showSlides(); // Show first slide immediately
