/**
 * SCROLL REVEAL – Intersection Observer para animaciones al hacer scroll
 * PsyAI Connect v1
 */

document.addEventListener('DOMContentLoaded', function () {
    const revealElements = document.querySelectorAll('.scroll-reveal');

    if ('IntersectionObserver' in window) {
        const revealOptions = {
            threshold: 0.15,
            rootMargin: '0px 0px -50px 0px'
        };

        const revealOnScroll = new IntersectionObserver(function (entries, observer) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Agregar clase para trigger de animación
                    entry.target.classList.add('is-visible');
                    
                    // Opcional: dejar de observar después de que se haya revelado
                    // observer.unobserve(entry.target);
                }
            });
        }, revealOptions);

        revealElements.forEach(element => {
            revealOnScroll.observe(element);
        });
    } else {
        // Fallback para navegadores sin Intersection Observer
        revealElements.forEach(element => {
            element.classList.add('is-visible');
        });
    }
});
