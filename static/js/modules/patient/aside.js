// JavaScript para Dashboard Paciente
// La lógica del aside se encuentra en /js/core/shared/aside.js (API: PsyAIAside.open/close/toggle/isOpen)
// Este archivo mantiene el menú inferior móvil y la inicialización del sidebar en páginas de paciente.
(function () {
    function isPatientPage() {
        return document.body.classList.contains('patient-dashboard');
    }

    function createBottomNav() {
        if (!isPatientPage() || document.querySelector('.mobile-bottom-nav[data-role="patient"]')) return;

        const items = [
            { href: '/', icon: 'fas fa-home', label: 'Inicio' },
            { href: 'aside-patient/chatbot.html', icon: 'fas fa-robot', label: 'Chatbot' },
            { href: 'aside-patient/agenda-quotes.html', icon: 'fas fa-calendar-alt', label: 'Agenda' },
            { href: 'aside-patient/mensajes.html', icon: 'fas fa-comments', label: 'Mensajes' },
            { href: 'aside-patient/evolution.html', icon: 'fas fa-chart-area', label: 'Evolucion' },
            { href: 'aside-patient/historia_clinica_paciente.html', icon: 'fas fa-file-medical', label: 'Documentos' },
            { href: 'aside-patient/my.profile.html', icon: 'fas fa-user-circle', label: 'Perfil' }
        ];

        const current = window.location.pathname.replace(/\\/g, '/');
        const nav = document.createElement('nav');
        nav.className = 'mobile-bottom-nav';
        nav.dataset.role = 'patient';
        nav.setAttribute('aria-label', 'Navegacion paciente');

        nav.innerHTML = items.map(item => {
            const target = item.href.replace(/^\//, '');
            const active = current.endsWith(target) || (target === 'patient.dashboard.html' && current.endsWith('/patient.dashboard.html'));
            return `<a class="mobile-bottom-nav__item${active ? ' active' : ''}" href="${item.href}"><i class="${item.icon}"></i><span>${item.label}</span></a>`;
        }).join('');

        document.body.classList.add('has-mobile-bottom-nav');
        document.body.appendChild(nav);
    }

    // ------------------------------------------------------------------
    // Inicialización del sidebar (mismo código que core/shared/aside.js)
    // ------------------------------------------------------------------
    function initSidebar() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        const overlay = document.getElementById('sidebarOverlay') || (function () {
            const el = document.createElement('div');
            el.className = 'sidebar-overlay';
            el.id = 'sidebarOverlay';
            document.body.appendChild(el);
            return el;
        })();

        const toggleBtn = document.getElementById('toggleSidebar') || document.getElementById('menuToggle') || document.querySelector('.menu-toggle, .toggle-btn');

        if (!toggleBtn) {
            const btn = document.createElement('button');
            btn.className = 'menu-toggle';
            btn.id = 'menuToggle';
            btn.innerHTML = '<i class="fas fa-bars"></i>';
            document.body.appendChild(btn);
            toggleBtn = btn;
        }

        if (!sidebar.id) sidebar.id = 'sidebar';
        if (!overlay.id) overlay.id = 'sidebarOverlay';

        toggleBtn.setAttribute('aria-controls', sidebar.id);
        toggleBtn.setAttribute('aria-expanded', 'false');

        const MOBILE_QUERY = '(max-width: 991.98px)';
        const mediaQuery = window.matchMedia(MOBILE_QUERY);

        function isMobile() {
            return mediaQuery.matches;
        }

        function lockBodyScroll(lock) {
            if (lock) {
                document.documentElement.classList.add('sidebar-open');
            } else {
                document.documentElement.classList.remove('sidebar-open');
            }
        }

        function setAnimating(animating) {
            if (animating) sidebar.classList.add('is-animating');
            else sidebar.classList.remove('is-animating');
        }

        function handleMediaChange() {
            if (!isMobile() && sidebar.classList.contains('active')) {
                closeSidebar();
            }
        }

        function openSidebar() {
            if (sidebar.classList.contains('active')) return;
            if (!isMobile()) return;

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
            const firstLink = sidebar.querySelector('.sidebar__nav-item, .nav-link');
            if (firstLink) firstLink.focus({ preventScroll: true });
        }

        function closeSidebar() {
            if (!sidebar.classList.contains('active')) return;

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
        }

        mediaQuery.addEventListener('change', handleMediaChange);
        handleMediaChange();

        toggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (sidebar.classList.contains('active')) closeSidebar(); else openSidebar();
        });

        overlay.addEventListener('click', function () {
            closeSidebar();
        });

        sidebar.addEventListener('click', function (e) {
            if (!isMobile()) return;
            const link = e.target.closest('.sidebar__nav-item, .nav-link, a');
            if (link && link.tagName === 'A') {
                closeSidebar();
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && sidebar.classList.contains('active') && isMobile()) {
                e.preventDefault();
                closeSidebar();
                toggleBtn.focus({ preventScroll: true });
            }
        });

        sidebar.addEventListener('transitionend', function (e) {
            if (e.propertyName === 'transform') {
                sidebar.classList.remove('is-animating');
            }
        });

        window.addEventListener('beforeunload', function () {
            sidebar.classList.remove('active', 'closing', 'is-animating');
            overlay.classList.remove('active', 'closing');
            toggleBtn.classList.remove('active');
            toggleBtn.setAttribute('aria-expanded', 'false');
            lockBodyScroll(false);
        });
        window.addEventListener('pagehide', function () {
            sidebar.classList.remove('active', 'closing', 'is-animating');
            overlay.classList.remove('active', 'closing');
            toggleBtn.classList.remove('active');
            toggleBtn.setAttribute('aria-expanded', 'false');
            lockBodyScroll(false);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            createBottomNav();
            initSidebar();
        });
    } else {
        createBottomNav();
        initSidebar();
    }
})();
