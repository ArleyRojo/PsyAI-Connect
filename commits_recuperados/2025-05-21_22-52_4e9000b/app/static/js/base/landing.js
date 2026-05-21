/* ═══════════════════════════════════════════════════════════ */
/* INDEX.JS — PsyAI Connect Landing Page                     */
/* Script para interactividad y efectos visuales             */
/* ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function() {
    
    /* ─────────────────────────────────────────────────────── */
    /* 1. AOS (Animate on Scroll) Initialization              */
    /* ─────────────────────────────────────────────────────── */
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            once: false,
            offset: 100,
            easing: 'ease-in-out-cubic',
            delay: 0,
            disable: 'mobile' // Deshabilitar en mobile para mejor performance
        });
    }
    
    /* ─────────────────────────────────────────────────────── */
    /* 2. Smooth Scroll for Anchor Links                      */
    /* ─────────────────────────────────────────────────────── */
    const smoothScrollLinks = document.querySelectorAll('a[href^="#"]:not([data-bs-toggle])');
    smoothScrollLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#' || href.includes('logoModal')) return;
            
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                const offsetTop = target.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    /* ─────────────────────────────────────────────────────── */
    /* 3. Navbar Scroll Effect                                */
    /* ─────────────────────────────────────────────────────── */
    const navbar = document.getElementById('mainNav');
    if (navbar) {
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollTop > 10) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }
    
    /* ─────────────────────────────────────────────────────── */
    /* 4. Mobile Menu Auto-Close                              */
    /* ─────────────────────────────────────────────────────── */
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    const navLinks = document.querySelectorAll('.navbar-collapse .nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                navbarToggler?.click();
            }
        });
    });
    
    /* ─────────────────────────────────────────────────────── */
    /* 5. Theme Toggle Functionality                          */
    /* ─────────────────────────────────────────────────────── */
    const themeToggle = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    
    if (themeToggle) {
        // Detectar tema guardado o preferencia del sistema
        function initializeTheme() {
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
                htmlElement.classList.add('dark-mode');
                document.body.classList.add('dark-mode');
            } else {
                htmlElement.classList.remove('dark-mode');
                document.body.classList.remove('dark-mode');
            }
        }
        
        themeToggle.addEventListener('click', function() {
            htmlElement.classList.toggle('dark-mode');
            document.body.classList.toggle('dark-mode');
            
            // Guardar preferencia
            const isDarkMode = htmlElement.classList.contains('dark-mode');
            localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
            
            // Agregar animación
            this.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                this.style.transform = 'rotate(0deg)';
            }, 400);
        });
        
        initializeTheme();
        
        // Escuchar cambios de preferencia del sistema
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (!localStorage.getItem('theme')) {
                initializeTheme();
            }
        });
    }
    
    /* ─────────────────────────────────────────────────────── */
    /* 6. Carousel Auto-Play                                 */
    /* ─────────────────────────────────────────────────────── */
    const heroCarousel = document.getElementById('heroCarousel');
    if (heroCarousel) {
        // Crear carousel de Bootstrap si existe
        try {
            const carousel = new bootstrap.Carousel(heroCarousel, {
                interval: 5000,
                wrap: true,
                pause: 'hover'
            });
        } catch (e) {
            console.log('Bootstrap Carousel not available');
        }
    }
    
    /* ─────────────────────────────────────────────────────── */
    /* 7. Counter Animation on Scroll                         */
    /* ─────────────────────────────────────────────────────── */
    function animateCounters() {
        const counters = document.querySelectorAll('[data-count]');
        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-count'));
            const duration = 2000;
            const start = 0;
            const increment = target / (duration / 16);
            
            let current = start;
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    counter.textContent = target;
                    clearInterval(timer);
                } else {
                    counter.textContent = Math.floor(current);
                }
            }, 16);
        });
    }
    
    // Ejecutar cuando los contadores sean visibles
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    const countersSection = document.querySelector('[data-counters]');
    if (countersSection) {
        observer.observe(countersSection);
    }
    
    /* ─────────────────────────────────────────────────────── */
    /* 8. Ripple Effect on Buttons                            */
    /* ─────────────────────────────────────────────────────── */
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        });
    });
    
    /* ─────────────────────────────────────────────────────── */
    /* 9. Parallax Effect on Scroll (Light Version)          */
    /* ─────────────────────────────────────────────────────── */
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('[data-parallax]');
        
        parallaxElements.forEach(element => {
            const yPos = scrolled * 0.5;
            element.style.transform = `translateY(${yPos}px)`;
        });
    });
    
    /* ─────────────────────────────────────────────────────── */
    /* 10. Performance Optimization - Lazy Loading Images    */
    /* ─────────────────────────────────────────────────────── */
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    imageObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    /* ─────────────────────────────────────────────────────── */
    /* 11. Add Ripple CSS Dynamically                         */
    /* ─────────────────────────────────────────────────────── */
    const style = document.createElement('style');
    style.textContent = `
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.6);
            transform: scale(0);
            animation: ripple-animation 0.6s ease-out;
            pointer-events: none;
        }
        
        @keyframes ripple-animation {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    /* ─────────────────────────────────────────────────────── */
    /* 12. Console Info                                       */
    /* ─────────────────────────────────────────────────────── */
    console.log('%c🧠 PsyAI Connect', 'color: #0D47A1; font-size: 20px; font-weight: bold;');
    console.log('%cBienestar Emocional Accesible', 'color: #90CAF9; font-size: 14px;');
    console.log('%c💙 Hecho con IA y cuidado', 'color: #1976D2; font-size: 12px;');
});

/* Performance: Defer non-critical initialization */
if (document.readyState === 'complete') {
    window.dispatchEvent(new Event('load'));
}
