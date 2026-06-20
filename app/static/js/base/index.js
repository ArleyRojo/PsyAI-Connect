document.addEventListener('DOMContentLoaded', function () {
    const nav = document.getElementById('mainNav');

    function syncNavbarState() {
        if (!nav) return;
        nav.classList.toggle('scrolled', window.scrollY > 16);
    }

    if (window.AOS && typeof window.AOS.init === 'function') {
        window.AOS.init({
            duration: 800,
            easing: 'ease-out-cubic',
            once: true,
            offset: 80
        });
    }

    syncNavbarState();
    window.addEventListener('scroll', syncNavbarState, { passive: true });
});
