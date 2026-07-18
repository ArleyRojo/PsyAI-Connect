/* ═══════════════════════════════════════════════════════════ */
/* NAVBAR SCROLL EFFECT - PsyAI Connect                      */
/* Agrega blur effect al navbar cuando el usuario hace scroll */
/* ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function() {
    const navbar = document.getElementById('mainNav');
    
    if (!navbar) return;
    
    let lastScrollTop = 0;
    const scrollThreshold = 10;
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > scrollThreshold) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    }, false);
    
    // Smooth scroll para los links internos
    const navLinks = document.querySelectorAll('a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            // No hacer scroll suave para los links especiales
            if (href === '#' || href.includes('logoModal')) return;
        });
    });
    
    // Cerrar navbar al hacer click en un link
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href').startsWith('#') && 
            !link.getAttribute('href').includes('logoModal')) {
            link.addEventListener('click', function() {
                if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                    navbarToggler.click();
                }
            });
        }
    });

    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function(event) {
            const target = this.dataset.modalTarget;
            if (!target) return;
            event.preventDefault();
            const modal = document.querySelector(target);
            if (modal && typeof bootstrap !== 'undefined') {
                const instance = bootstrap.Modal.getOrCreateInstance(modal);
                instance.show();
            }
        });
    });
});

/* Smooth scroll behavior enhancement */
if (typeof AOS !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        AOS.init({
            duration: 800,
            once: false,
            offset: 100,
            easing: 'ease-in-out-cubic'
        });
    });
}
