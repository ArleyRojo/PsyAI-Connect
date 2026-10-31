(function () {
    'use strict';

    const destinations = {
        ver_agenda: '/aside-professional/my.agenda.html',
        ver_reportes: '/aside-professional/reports.html',
        ver_pacientes: '/aside-professional/patients.html'
    };

    function createMessage(text, className) {
        const message = document.createElement('p');
        message.className = className;
        message.textContent = text;
        return message;
    }

    function setAlerts(alerts) {
        const safeAlerts = Array.isArray(alerts) ? alerts : [];

        document.querySelectorAll('[data-professional-notification-count]').forEach((badge) => {
            badge.textContent = safeAlerts.length > 99 ? '99+' : String(safeAlerts.length);
            badge.hidden = safeAlerts.length === 0;
            if (badge.id === 'notifBadge') {
                badge.style.display = safeAlerts.length ? 'inline' : 'none';
            }
        });

        document.querySelectorAll('[data-professional-notification-list]').forEach((list) => {
            list.replaceChildren();
            if (!safeAlerts.length) {
                list.append(createMessage('No tienes avisos pendientes.', 'professional-notification-empty'));
                return;
            }

            safeAlerts.forEach((alert) => {
                const item = document.createElement('article');
                item.className = 'professional-notification-item';
                const title = document.createElement('div');
                title.className = 'professional-notification-item__title';
                title.textContent = alert.titulo || 'Aviso';
                const message = createMessage(
                    alert.mensaje || '',
                    'professional-notification-item__message'
                );
                item.append(title, message);

                const destination = destinations[alert.accion];
                if (destination) {
                    const link = document.createElement('a');
                    link.className = 'professional-notification-action';
                    link.href = destination;
                    link.textContent = 'Ver detalle';
                    item.append(link);
                }
                list.append(item);
            });
        });
    }

    async function loadAlerts() {
        const response = await fetch('/api/profesional/dashboard', {
            credentials: 'include',
            headers: { Accept: 'application/json' }
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.message || 'No se pudieron cargar los avisos.');
        }
        setAlerts(data.alertas);
    }

    function initialize() {
        const wrappers = Array.from(document.querySelectorAll('[data-professional-notifications]'));
        if (!wrappers.length) return;

        wrappers.forEach((wrapper) => {
            const toggle = wrapper.querySelector('[data-professional-notification-toggle]');
            const panel = wrapper.querySelector('[data-professional-notification-panel]');
            const close = wrapper.querySelector('[data-professional-notification-close]');
            if (!toggle || !panel) return;

            const closePanel = () => {
                panel.hidden = true;
                toggle.setAttribute('aria-expanded', 'false');
            };

            toggle.addEventListener('click', async () => {
                const opening = panel.hidden;
                panel.hidden = !opening;
                toggle.setAttribute('aria-expanded', String(opening));
                if (!opening) return;

                const list = wrapper.querySelector('[data-professional-notification-list]');
                list.replaceChildren(createMessage('Cargando avisos…', 'professional-notification-empty'));
                try {
                    await loadAlerts();
                } catch (error) {
                    list.replaceChildren(createMessage(
                        error.message || 'No se pudieron cargar los avisos.',
                        'professional-notification-empty'
                    ));
                }
            });

            close?.addEventListener('click', closePanel);
            document.addEventListener('click', (event) => {
                if (!wrapper.contains(event.target)) closePanel();
            });
            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape') closePanel();
            });
        });

        window.addEventListener('psyai:professional-alerts', (event) => setAlerts(event.detail));
        if (!window.location.pathname.endsWith('/professional.dashboard.html')) {
            loadAlerts().catch(() => setAlerts([]));
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize, { once: true });
    } else {
        initialize();
    }
})();
