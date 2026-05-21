// JavaScript para Dashboard Responsive (Chatbot y todas las páginas del paciente)
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) {
        return;
    }

    const STORAGE_KEY = 'psyai_ui_state';

    function getStoredState() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            return stored ? JSON.parse(stored) : {};
        } catch (e) {
            return {};
        }
    }

    function saveSidebarState(isOpen) {
        try {
            const state = getStoredState();
            state.sidebarOpen = isOpen;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (e) {}
    }

    const storedState = getStoredState();

    // Crear botón hamburguesa si no existe
    // Priorizar 'toggleSidebar' (usado en HTML) sobre 'menuToggle'
    let menuToggle = document.getElementById('toggleSidebar') || document.getElementById('menuToggle');
    
    if (!menuToggle) {
        menuToggle = document.createElement('button');
        menuToggle.className = 'menu-toggle';
        menuToggle.id = 'menuToggle';
        menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        document.body.appendChild(menuToggle);
    }

    // Crear overlay si no existe
    let overlay = document.getElementById('sidebarOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.id = 'sidebarOverlay';
        document.body.appendChild(overlay);
    }

    let closeTimer = null;

    const setToggleIcon = (isOpen) => {
        if (!menuToggle) return;

        menuToggle.setAttribute('aria-label', isOpen ? 'Cerrar menú' : 'Abrir menú');
        const icon = menuToggle.querySelector('i');

        if (icon) {
            icon.classList.toggle('fa-bars', !isOpen);
            icon.classList.toggle('fa-xmark', isOpen);
            icon.classList.remove('fa-times');
            return;
        }

        menuToggle.innerHTML = isOpen ? '<i class="fas fa-xmark"></i>' : '<i class="fas fa-bars"></i>';
    };

    const hideSidebarImmediately = () => {
        if (closeTimer) {
            clearTimeout(closeTimer);
            closeTimer = null;
        }

        overlay.classList.remove('active', 'closing');
        sidebar.classList.remove('active', 'closing');
        if (menuToggle) {
            menuToggle.classList.remove('active');
            menuToggle.setAttribute('aria-expanded', 'false');
            setToggleIcon(false);
        }
    };

    const openSidebar = () => {
        if (closeTimer) {
            clearTimeout(closeTimer);
            closeTimer = null;
        }
        overlay.classList.remove('closing');
        sidebar.classList.remove('closing');
        sidebar.classList.add('active');
        overlay.classList.add('active');
        if (menuToggle) {
            menuToggle.classList.add('active');
            menuToggle.setAttribute('aria-expanded', 'true');
            setToggleIcon(true);
        }
        saveSidebarState(true);
    };

    const closeSidebar = () => {
        if (!sidebar.classList.contains('active')) {
            return;
        }

        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        overlay.classList.add('closing');
        if (menuToggle) {
            menuToggle.classList.remove('active');
            menuToggle.setAttribute('aria-expanded', 'false');
            setToggleIcon(false);
        }

        if (closeTimer) {
            clearTimeout(closeTimer);
        }

        closeTimer = setTimeout(() => {
            overlay.classList.remove('closing');
            closeTimer = null;
        }, 320);

        saveSidebarState(false);
    };

    // Restore sidebar state from localStorage on page load
    // Por defecto cerrados al navegar entre páginas
    if (storedState.sidebarOpen === true) {
        setTimeout(function() {
            openSidebar();
        }, 100);
    } else {
        // Asegurar que esté cerrado al cargar nueva página
        hideSidebarImmediately();
        saveSidebarState(false);
    }

    // Toggle sidebar al hacer clic en el botón
    menuToggle.addEventListener('click', function() {
        if (sidebar.classList.contains('active')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    // Cerrar sidebar al hacer clic en el overlay
    overlay.addEventListener('click', closeSidebar);

    // Cerrar sidebar al hacer clic en un enlace (solo en móvil)
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 991) {
                hideSidebarImmediately();
            }
        });
    });

    // Ajustar al cambiar tamaño de ventana
    window.addEventListener('resize', function() {
        if (window.innerWidth > 991) {
            closeSidebar();
        }
    });

    window.addEventListener('beforeunload', function() {
        hideSidebarImmediately();
        saveSidebarState(false);
    });
    window.addEventListener('pagehide', function() {
        hideSidebarImmediately();
        saveSidebarState(false);
    });

    let touchStartX = 0;
    let touchStartY = 0;
    let touchStartedAtEdge = false;

    function isTabletSidebarViewport() {
        return window.innerWidth >= 768 && window.innerWidth <= 991;
    }

    document.addEventListener('touchstart', function(event) {
        if (!isTabletSidebarViewport() || !event.touches || event.touches.length !== 1) return;
        const touch = event.touches[0];
        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
        touchStartedAtEdge = touchStartX <= 30;
    }, { passive: true });

    document.addEventListener('touchend', function(event) {
        if (!isTabletSidebarViewport() || !event.changedTouches || event.changedTouches.length !== 1) return;
        const touch = event.changedTouches[0];
        const deltaX = touch.clientX - touchStartX;
        const deltaY = Math.abs(touch.clientY - touchStartY);
        if (deltaY > 60 || Math.abs(deltaX) < 70) return;
        if (deltaX > 0 && touchStartedAtEdge) openSidebar();
        if (deltaX < 0) closeSidebar();
    }, { passive: true });
});

(function () {
    function isPatientPage() {
        return window.location.pathname.includes('/patient') || window.location.pathname.includes('patient.dashboard');
    }

    function createBottomNav() {
        if (!isPatientPage() || document.querySelector('.mobile-bottom-nav[data-role="patient"]')) return;

        const items = [
            { href: 'patient.dashboard.html', icon: 'fas fa-home', label: 'Inicio' },
            { href: 'aside-patient/chatbot.html', icon: 'fas fa-robot', label: 'Chatbot' },
            { href: 'aside-patient/agenda-quotes.html', icon: 'fas fa-calendar-alt', label: 'Agenda' },
            { href: 'aside-patient/evolution.html', icon: 'fas fa-chart-area', label: 'Evolucion' },
            { href: 'aside-patient/my.profile.html', icon: 'fas fa-user-circle', label: 'Perfil' }
        ];

        const current = window.location.pathname.replace(/\\/g, '/');
        const nav = document.createElement('nav');
        nav.className = 'mobile-bottom-nav';
        nav.dataset.role = 'patient';
        nav.setAttribute('aria-label', 'Navegación paciente');

        nav.innerHTML = items.map(item => {
            const target = item.href.replace(/^\//, '');
            const active = current.endsWith(target) || (target === 'patient.dashboard.html' && current.endsWith('/patient.dashboard.html'));
            return `<a class="mobile-bottom-nav__item${active ? ' active' : ''}" href="${item.href}"><i class="${item.icon}"></i><span>${item.label}</span></a>`;
        }).join('');

        document.body.classList.add('has-mobile-bottom-nav');
        document.body.appendChild(nav);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createBottomNav);
    } else {
        createBottomNav();
    }
})();
