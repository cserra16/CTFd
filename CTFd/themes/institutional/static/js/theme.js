// Simple fade-in on scroll effect
function onScroll() {
    document.querySelectorAll('.fade-in').forEach(function(el) {
        var rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight - 50) {
            el.classList.add('visible');
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    onScroll();
    document.addEventListener('scroll', onScroll, { passive: true });
    var menuToggle = document.querySelector('.navbar-toggler');
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            document.querySelector('.navbar-collapse').classList.toggle('show');
        });
    }
});
