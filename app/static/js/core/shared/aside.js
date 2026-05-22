// Sidebar toggle compartido (admin + professional dashboard)
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
    let menuToggle = document.getElementById('menuToggle') || document.getElementById('toggleSidebar');
    
    if (!menuToggle) {
        menuToggle = document.createElement('button');
        menuToggle.className = 'menu-toggle';
        menuToggle.id = 'menuToggle';
        menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        document.body.appendChild(menuToggle);
    }

    if (!sidebar.id) {
        sidebar.id = 'sidebar';
    }
    menuToggle.setAttribute('aria-controls', sidebar.id || 'sidebar');
    menuToggle.setAttribute('aria-expanded', 'false');

    // Crear overlay si no existe
    let overlay = document.getElementById('sidebarOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.id = 'sidebarOverlay';
        document.body.appendChild(overlay);
    }

    let closeTimer = null;

    const hideSidebarImmediately = () => {
        if (closeTimer) {
            clearTimeout(closeTimer);
            closeTimer = null;
        }

        overlay.classList.remove('active', 'closing');
        sidebar.classList.remove('active', 'closing');
        menuToggle.classList.remove('active');
        menuToggle.setAttribute('aria-expanded', 'false');
        saveSidebarState(false);
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
        menuToggle.classList.add('active');
        menuToggle.setAttribute('aria-expanded', 'true');
        saveSidebarState(true);
    };

    const closeSidebar = () => {
        if (!sidebar.classList.contains('active')) {
            return;
        }

        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        overlay.classList.add('closing');
        menuToggle.classList.remove('active');
        menuToggle.setAttribute('aria-expanded', 'false');

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
    if (storedState.sidebarOpen === true) {
        setTimeout(function() {
            openSidebar();
        }, 100);
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

    window.addEventListener('beforeunload', hideSidebarImmediately);
    window.addEventListener('pagehide', hideSidebarImmediately);

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
    function createProfessionalBottomNav() {
        const current = window.location.pathname.replace(/\\/g, '/');
        const isProfessional = current.includes('/professional') || current.endsWith('/professional.dashboard.html');
        if (!isProfessional || document.querySelector('.mobile-bottom-nav[data-role="professional"]')) return;

        const items = [
            { href: '/professional.dashboard.html', icon: 'fas fa-home', label: 'Inicio' },
            { href: '/aside-professional/patients.html', icon: 'fas fa-users', label: 'Pacientes' },
            { href: '/aside-professional/my.agenda.html', icon: 'fas fa-calendar-check', label: 'Agenda' },
            { href: '/aside-professional/mensajes.html', icon: 'fas fa-comments', label: 'Mensajes' },
            { href: '/aside-professional/reports.html', icon: 'fas fa-chart-line', label: 'Reportes' },
            { href: '/aside-professional/my.profile2.html', icon: 'fas fa-user-circle', label: 'Perfil' }
        ];

        const nav = document.createElement('nav');
        nav.className = 'mobile-bottom-nav';
        nav.dataset.role = 'professional';
        nav.setAttribute('aria-label', 'Navegacion profesional');
        nav.innerHTML = items.map(item => {
            const target = item.href.replace(/^\//, '');
            const active = current.endsWith(target) || (target === 'professional.dashboard.html' && current.endsWith('/professional.dashboard.html'));
            return `<a class="mobile-bottom-nav__item${active ? ' active' : ''}" href="${item.href}"><i class="${item.icon}"></i><span>${item.label}</span></a>`;
        }).join('');

        document.body.classList.add('has-mobile-bottom-nav');
        document.body.appendChild(nav);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createProfessionalBottomNav);
    } else {
        createProfessionalBottomNav();
    }
})();
