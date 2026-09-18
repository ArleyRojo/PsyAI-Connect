document.addEventListener('DOMContentLoaded', function () {
    const nav = document.getElementById('mainNav');
    const progressBar = nav ? nav.querySelector('.navbar-progress') : null;

    function syncNavbarState() {
        if (!nav) return;
        const scrolled = window.scrollY > 16;
        nav.classList.toggle('scrolled', scrolled);

        if (progressBar) {
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const pct = docHeight > 0 ? Math.min((window.scrollY / docHeight) * 100, 100) : 0;
            progressBar.style.width = pct + '%';
        }
    }

    function setupActiveSectionObserver() {
        if (!nav) return;
        const links = nav.querySelectorAll('.nav-link[href^="#"]');
        if (!links.length) return;

        const sections = [];
        links.forEach(function (link) {
            const id = link.getAttribute('href');
            if (id && id.length > 1) {
                const el = document.querySelector(id);
                if (el) sections.push({ id: id, el: el, link: link });
            }
        });
        if (!sections.length) return;

        function clearActive() {
            sections.forEach(function (s) { s.link.classList.remove('active'); });
        }

        function activateById(id) {
            sections.forEach(function (s) {
                s.link.classList.toggle('active', s.id === id);
            });
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    activateById('#' + entry.target.id);
                }
            });
        }, {
            rootMargin: '-20% 0px -60% 0px',
            threshold: 0
        });

        sections.forEach(function (s) { observer.observe(s.el); });
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
    setupActiveSectionObserver();

    // Animate section title underlines on scroll
    var sectionTitles = document.querySelectorAll('.section-title');
    if (sectionTitles.length) {
        var titleObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animated');
                    titleObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        sectionTitles.forEach(function (t) { titleObserver.observe(t); });
    }
});
