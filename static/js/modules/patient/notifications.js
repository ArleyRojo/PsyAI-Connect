(function () {
    'use strict';

    const toggle = document.getElementById('patientNotificationsToggle');
    const panel = document.getElementById('patientNotificationsPanel');
    const list = document.getElementById('patientNotificationsList');
    const badge = document.getElementById('patientNotificationsBadge');
    const wrapper = document.getElementById('patientNotifications');
    if (!toggle || !panel || !list || !badge || !wrapper) return;

    let knownIds = null;

    function updateBadge(count) {
        const total = Number(count) || 0;
        badge.textContent = total > 99 ? '99+' : String(total);
        badge.hidden = total === 0;
    }

    function escapeAlertText(value) {
        return String(value ?? '').replace(/[&<>"']/g, (character) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        })[character]);
    }

    function render(notifications) {
        list.replaceChildren();
        if (!notifications.length) {
            const empty = document.createElement('p');
            empty.className = 'patient-notifications__empty';
            empty.textContent = 'No tienes notificaciones por ahora.';
            list.appendChild(empty);
            return;
        }

        notifications.forEach((notification) => {
            const item = document.createElement('article');
            item.className = 'patient-notifications__item';

            const title = document.createElement('div');
            title.className = 'patient-notifications__item-title';
            title.textContent = notification.titulo || 'Notificación';

            const message = document.createElement('p');
            message.className = 'patient-notifications__item-message';
            message.textContent = notification.mensaje || '';
            item.append(title, message);

            if (notification.fecha) {
                const date = new Date(notification.fecha);
                if (!Number.isNaN(date.getTime())) {
                    const dateLabel = document.createElement('time');
                    dateLabel.className = 'patient-notifications__item-date';
                    dateLabel.dateTime = notification.fecha;
                    dateLabel.textContent = new Intl.DateTimeFormat('es-CO', {
                        dateStyle: 'medium',
                        timeStyle: 'short'
                    }).format(date);
                    item.appendChild(dateLabel);
                }
            }

            list.appendChild(item);
        });
    }

    async function loadNotifications(showNewAlerts) {
        const response = await fetch('/api/paciente/notificaciones', {
            credentials: 'include',
            headers: { Accept: 'application/json' }
        });
        if (!response.ok) throw new Error('No se pudieron cargar las notificaciones.');

        const data = await response.json();
        if (!data.success) throw new Error(data.message || 'No se pudieron cargar las notificaciones.');

        const notifications = Array.isArray(data.notificaciones) ? data.notificaciones : [];
        const ids = new Set(notifications.map((item) => item.idNotificacion));
        const newUnread = knownIds === null
            ? notifications.filter((item) => !item.leido).slice(0, 1)
            : notifications.filter((item) => !item.leido && !knownIds.has(item.idNotificacion));

        if (showNewAlerts && window.PsyAIAlerts?.info) {
            newUnread.forEach((item) => window.PsyAIAlerts.info(
                escapeAlertText(item.mensaje),
                escapeAlertText(item.titulo)
            ));
        }

        knownIds = new Set([...(knownIds || []), ...ids]);
        updateBadge(data.no_leidas);
        if (!panel.hidden) render(notifications);
        return notifications;
    }

    async function markNotificationsRead() {
        const response = await fetch('/api/paciente/notificaciones', {
            method: 'POST',
            credentials: 'include',
            headers: { Accept: 'application/json' }
        });
        if (response.ok) updateBadge(0);
    }

    toggle.addEventListener('click', async () => {
        const opening = panel.hidden;
        panel.hidden = !opening;
        toggle.setAttribute('aria-expanded', String(opening));
        if (!opening) return;

        try {
            const notifications = await loadNotifications(false);
            render(notifications);
            await markNotificationsRead();
        } catch (error) {
            list.replaceChildren();
            const message = document.createElement('p');
            message.className = 'patient-notifications__empty';
            message.textContent = error.message || 'No se pudieron cargar las notificaciones.';
            list.appendChild(message);
        }
    });

    document.getElementById('patientNotificationsClose')?.addEventListener('click', () => {
        panel.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
    });

    document.addEventListener('click', (event) => {
        if (!wrapper.contains(event.target)) {
            panel.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            panel.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
        }
    });

    loadNotifications(true).catch((error) => console.warn(error.message));
    window.setInterval(() => {
        loadNotifications(true).catch((error) => console.warn(error.message));
    }, 45000);
})();
