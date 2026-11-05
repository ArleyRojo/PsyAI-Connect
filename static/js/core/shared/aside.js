// Sidebar toggle unificado (admin + profesional + paciente)
// API pequeña: PsyAIAside.open(), .close(), .toggle(), .isOpen()
// Solo afecta móvil/tablet (≤ 991.98px). En PC el aside permanece fijo.
(function () {
    'use strict';

    const MOBILE_QUERY = '(max-width: 991.98px)';
    const TRANSITION_MS = 280;
    const ANIMATING_CLASS = 'is-animating';
    const SCROLL_LOCK_CLASS = 'sidebar-open';

    let sidebar = null;
    let overlay = null;
    let toggleBtn = null;
    let mediaQuery = null;
    let isAnimating = false;
    let rafId = null;

    // ------------------------------------------------------------------
    // Utilidades
    // ------------------------------------------------------------------
    function isMobile() {
        return mediaQuery ? mediaQuery.matches : window.matchMedia(MOBILE_QUERY).matches;
    }

    function getSidebar() {
        return document.querySelector('.sidebar');
    }

    function getOverlay() {
        return document.getElementById('sidebarOverlay') || document.querySelector('.sidebar-overlay');
    }

    function getToggle() {
        return document.getElementById('toggleSidebar') || document.getElementById('menuToggle') || document.querySelector('.menu-toggle, .toggle-btn');
    }

    function raf(fn) {
        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(fn);
    }

    function lockBodyScroll(lock) {
        if (lock) {
            document.documentElement.classList.add(SCROLL_LOCK_CLASS);
        } else {
            document.documentElement.classList.remove(SCROLL_LOCK_CLASS);
        }
    }

    function setAnimating(animating) {
        isAnimating = animating;
        if (sidebar) {
            if (animating) sidebar.classList.add(ANIMATING_CLASS);
            else sidebar.classList.remove(ANIMATING_CLASS);
        }
    }

    // ------------------------------------------------------------------
    // API pública
    // ------------------------------------------------------------------
    const PsyAIAside = {
        isOpen: function () {
            return sidebar ? sidebar.classList.contains('active') : false;
        },

        open: function () {
            if (!sidebar || !overlay || !toggleBtn) return;
            if (sidebar.classList.contains('active')) return;
            if (!isMobile()) return; // En PC no hace nada

            raf(function () {
                setAnimating(true);
                sidebar.classList.remove('closing');
                sidebar.classList.add('active');
                overlay.classList.remove('closing');
                overlay.classList.add('active');
                toggleBtn.classList.add('active');
                toggleBtn.setAttribute('aria-expanded', 'true');
                sidebar.removeAttribute('aria-hidden');
                sidebar.removeAttribute('inert');
                overlay.removeAttribute('aria-hidden');
                overlay.removeAttribute('inert');
                lockBodyScroll(true);
                // Focus primer enlace del aside
                const firstLink = sidebar.querySelector('.sidebar__nav-item, .nav-link');
                if (firstLink) firstLink.focus({ preventScroll: true });
            });
        },

        close: function () {
            if (!sidebar || !overlay || !toggleBtn) return;
            if (!sidebar.classList.contains('active')) return;

            raf(function () {
                setAnimating(true);
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
                overlay.classList.add('closing');
                toggleBtn.classList.remove('active');
                toggleBtn.setAttribute('aria-expanded', 'false');
                sidebar.setAttribute('aria-hidden', 'true');
                sidebar.setAttribute('inert', 'true');
                overlay.setAttribute('aria-hidden', 'true');
                overlay.setAttribute('inert', 'true');
                lockBodyScroll(false);
            });
        },

        toggle: function () {
            if (this.isOpen()) this.close(); else this.open();
        },
    };

    // Exponer global
    window.PsyAIAside = PsyAIAside;

    // Quitar no-transition tras el primer pintado para permitir animaciones posteriores
    document.documentElement.classList.add('no-transition');
    window.addEventListener('load', function () {
        document.documentElement.classList.remove('no-transition');
    });

    // ------------------------------------------------------------------
    // Inicialización
    // ------------------------------------------------------------------
    function init() {
        sidebar = getSidebar();
        if (!sidebar) return; // No hay aside en esta página

        overlay = getOverlay();
        toggleBtn = getToggle();

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'sidebar-overlay';
            overlay.id = 'sidebarOverlay';
            document.body.appendChild(overlay);
        }

        if (!toggleBtn) {
            toggleBtn = document.createElement('button');
            toggleBtn.className = 'menu-toggle';
            toggleBtn.id = 'menuToggle';
            toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
            document.body.appendChild(toggleBtn);
        }

        if (!sidebar.id) sidebar.id = 'sidebar';
        if (!overlay.id) overlay.id = 'sidebarOverlay';

        toggleBtn.setAttribute('aria-controls', sidebar.id);
        toggleBtn.setAttribute('aria-expanded', 'false');

        mediaQuery = window.matchMedia(MOBILE_QUERY);

        // En móvil, cerrado por defecto (no restaurar de localStorage)
        // En PC, el sidebar permanece visible y navegable (sin aria-hidden/inert)
        if (isMobile()) {
            sidebar.setAttribute('aria-hidden', 'true');
            sidebar.setAttribute('inert', 'true');
            overlay.setAttribute('aria-hidden', 'true');
            overlay.setAttribute('inert', 'true');
        } else {
            sidebar.removeAttribute('aria-hidden');
            sidebar.removeAttribute('inert');
            overlay.removeAttribute('aria-hidden');
            overlay.removeAttribute('inert');
        }

        function handleMediaChange() {
            if (!isMobile()) {
                // Pasando a PC: cerrar y limpiar clases de móvil
                PsyAIAside.close();
                sidebar.classList.remove('active', 'closing');
                overlay.classList.remove('active', 'closing');
                sidebar.removeAttribute('aria-hidden');
                sidebar.removeAttribute('inert');
                overlay.removeAttribute('aria-hidden');
                overlay.removeAttribute('inert');
                toggleBtn.setAttribute('aria-expanded', 'false');
                lockBodyScroll(false);
            } else {
                // Volviendo a móvil: asegurar cerrado
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
                toggleBtn.classList.remove('active');
                toggleBtn.setAttribute('aria-expanded', 'false');
                sidebar.setAttribute('aria-hidden', 'true');
                sidebar.setAttribute('inert', 'true');
                overlay.setAttribute('aria-hidden', 'true');
                overlay.setAttribute('inert', 'true');
                lockBodyScroll(false);
            }
        }

        mediaQuery.addEventListener('change', handleMediaChange);
        handleMediaChange(); // Ejecutar inmediatamente para asegurar estado correcto en PC y móvil

        // Click botón hamburguesa
        toggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            PsyAIAside.toggle();
        });

        // Click overlay cierra
        overlay.addEventListener('click', function () {
            PsyAIAside.close();
        });

        // Clic en enlace del menú cierra el aside
        sidebar.addEventListener('click', function (e) {
            if (!isMobile()) return;
            const link = e.target.closest('.sidebar__nav-item, .nav-link, a');
            if (link && link.tagName === 'A') {
                PsyAIAside.close();
            }
        });

        // Tecla Esc cierra
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && PsyAIAside.isOpen() && isMobile()) {
                e.preventDefault();
                PsyAIAside.close();
                // Devolver foco al botón
                toggleBtn.focus({ preventScroll: true });
            }
        });

        // Transition end para limpiar is-animating
        sidebar.addEventListener('transitionend', function (e) {
            if (e.propertyName === 'transform') {
                setAnimating(false);
            }
        });

        // beforeunload / pagehide: asegurar cerrado sin animación
        window.addEventListener('beforeunload', function () {
            sidebar.classList.remove('active', 'closing', ANIMATING_CLASS);
            overlay.classList.remove('active', 'closing');
            toggleBtn.classList.remove('active');
            toggleBtn.setAttribute('aria-expanded', 'false');
            lockBodyScroll(false);
        });
        window.addEventListener('pagehide', function () {
            sidebar.classList.remove('active', 'closing', ANIMATING_CLASS);
            overlay.classList.remove('active', 'closing');
            toggleBtn.classList.remove('active');
            toggleBtn.setAttribute('aria-expanded', 'false');
            lockBodyScroll(false);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
