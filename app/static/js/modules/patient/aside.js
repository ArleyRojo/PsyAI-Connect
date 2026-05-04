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
    let menuToggle = document.getElementById('menuToggle') || document.getElementById('toggleSidebar');
    
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

    const hideSidebarImmediately = () => {
        if (closeTimer) {
            clearTimeout(closeTimer);
            closeTimer = null;
        }

        overlay.classList.remove('active', 'closing');
        sidebar.classList.remove('active', 'closing');
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
        saveSidebarState(true);
    };

    const closeSidebar = () => {
        if (!sidebar.classList.contains('active')) {
            return;
        }

        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        overlay.classList.add('closing');

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
});
