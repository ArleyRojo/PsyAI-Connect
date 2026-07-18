// ============================================================
// PsyAI Alerts + Toasts - Unified
// ============================================================

// Global limit for all notifications on page
const PsyAINotifications = {
    maxTotal: 3,

    checkLimit() {
        const all = document.querySelectorAll('.psyai-alert, .psyai-toast');
        while (all.length >= this.maxTotal) {
            all[0].remove();
            all.shift();
        }
    }
};

// ----- CUSTOM ALERTS -----
const PsyAIAlerts = {
    container: null,
    maxMessageLength: 150,
    alertCount: 0,

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'psyai-alert-container';
            document.body.appendChild(this.container);
        }
    },

    show(options) {
        this.init();
        PsyAINotifications.checkLimit();

        if (options.message && options.message.length > this.maxMessageLength) {
            options.message = options.message.substring(0, this.maxMessageLength) + '...';
        }

        const { type = 'info', title, message, duration = 4000, icon } = options;

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-circle-xmark',
            warning: 'fa-triangle-exclamation',
            info: 'fa-circle-info',
            welcome: 'fa-hand-sparkles',
            reminder: 'fa-bell'
        };

        const alertEl = document.createElement('div');
        alertEl.className = `psyai-alert psyai-alert--${type}`;
        alertEl.innerHTML = `
            <div class="psyai-alert__icon">
                <i class="fas ${icon || icons[type]}"></i>
            </div>
            <div class="psyai-alert__content">
                ${title ? `<div class="psyai-alert__title">${title}</div>` : ''}
                <div class="psyai-alert__message">${message}</div>
            </div>
            <button class="psyai-alert__close" onclick="PsyAIAlerts.close(this.parentElement)">
                <i class="fas fa-xmark"></i>
            </button>
            <div class="psyai-alert__progress"></div>
        `;

        this.container.appendChild(alertEl);
        this.alertCount++;

        if (duration > 0) {
            setTimeout(() => this.close(alertEl), duration);
        }

        return alertEl;
    },

    close(alertEl) {
        if (!alertEl || alertEl.classList.contains('psyai-alert--closing')) return;
        alertEl.classList.add('psyai-alert--closing');
        this.alertCount = Math.max(0, this.alertCount - 1);
        setTimeout(() => {
            alertEl.remove();
            this.updatePositions();
        }, 300);
    },

    updatePositions() {
        const alerts = this.container.querySelectorAll('.psyai-alert');
        alerts.forEach((alert, index) => {
            alert.style.setProperty('--alert-index', index);
        });
    },

    success(message, title = '¡Éxito!') {
        return this.show({ type: 'success', title, message });
    },

    error(message, title = 'Error') {
        return this.show({ type: 'error', title, message, duration: 5000 });
    },

    warning(message, title = 'Advertencia') {
        return this.show({ type: 'warning', title, message });
    },

    info(message, title = 'Información') {
        return this.show({ type: 'info', title, message });
    },

    welcome(name, role = 'paciente') {
        const messages = {
            paciente: `Bienvenido a PsyAI Connect, ${name}. Tu bienestar emocional es nuestra prioridad.`,
            profesional: `Bienvenido, Dr(a). ${name}. Tienes pacientes esperando tu atención.`,
            admin: `Bienvenido al panel de administración, ${name}.`
        };
        return this.show({ type: 'welcome', title: '¡Bienvenido!', message: messages[role] || messages.paciente });
    },

    reminder(title, message) {
        return this.show({ type: 'reminder', title, message, icon: 'fa-bell' });
    }
};

function showAlert(type, message, title) {
    return PsyAIAlerts[type] ? PsyAIAlerts[type](message, title) : PsyAIAlerts.info(message, title);
}

// ----- TOASTS -----
(function () {

    function getToastContainer() {
        let c = document.getElementById('toast-container');
        if (!c) {
            c = document.createElement('div');
            c.id = 'toast-container';
            document.body.appendChild(c);
        }
        return c;
    }

    const TIPOS = {
        success: {
            light: { bg:'rgba(240,253,244,0.96)', border:'rgba(134,239,172,0.55)', iconBg:'linear-gradient(135deg,#16a34a,#4ade80)', iconShadow:'rgba(22,163,74,0.3)', text:'#14532d', subtext:'#166534', progress:'#16a34a' },
            dark:  { bg:'rgba(5,46,22,0.93)',     border:'rgba(22,101,52,0.65)',   iconBg:'linear-gradient(135deg,#15803d,#4ade80)', iconShadow:'rgba(74,222,128,0.25)', text:'#bbf7d0', subtext:'#86efac', progress:'#4ade80' },
            svg:   `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
            label: 'Éxito',
        },
        danger: {
            light: { bg:'rgba(254,242,242,0.96)', border:'rgba(252,165,165,0.55)', iconBg:'linear-gradient(135deg,#dc2626,#f87171)', iconShadow:'rgba(220,38,38,0.3)', text:'#7f1d1d', subtext:'#991b1b', progress:'#dc2626' },
            dark:  { bg:'rgba(45,10,10,0.93)',    border:'rgba(153,27,27,0.65)',   iconBg:'linear-gradient(135deg,#b91c1c,#f87171)', iconShadow:'rgba(248,113,113,0.25)', text:'#fecaca', subtext:'#fca5a5', progress:'#f87171' },
            svg:   `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
            label: 'Error',
        },
        warning: {
            light: { bg:'rgba(255,251,235,0.96)', border:'rgba(252,211,77,0.55)', iconBg:'linear-gradient(135deg,#d97706,#fbbf24)', iconShadow:'rgba(217,119,6,0.3)', text:'#78350f', subtext:'#92400e', progress:'#d97706' },
            dark:  { bg:'rgba(28,18,0,0.93)',     border:'rgba(146,64,14,0.65)',  iconBg:'linear-gradient(135deg,#b45309,#fbbf24)', iconShadow:'rgba(251,191,36,0.25)', text:'#fef08a', subtext:'#fde68a', progress:'#fbbf24' },
            svg:   `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
            label: 'Atención',
        },
        info: {
            light: { bg:'rgba(239,246,255,0.96)', border:'rgba(147,197,253,0.55)', iconBg:'linear-gradient(135deg,#2563eb,#60a5fa)', iconShadow:'rgba(37,99,235,0.3)', text:'#1e3a8a', subtext:'#1e40af', progress:'#2563eb' },
            dark:  { bg:'rgba(10,22,40,0.93)',    border:'rgba(30,64,175,0.65)',   iconBg:'linear-gradient(135deg,#1d4ed8,#60a5fa)', iconShadow:'rgba(96,165,250,0.25)', text:'#bfdbfe', subtext:'#93c5fd', progress:'#60a5fa' },
            svg:   `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
            label: 'Info',
        },
    };

    if (!document.getElementById('toast-styles')) {
        const s = document.createElement('style');
        s.id = 'toast-styles';
        s.textContent = `
            #toast-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 99999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
                width: 360px;
            }
            @keyframes _tIn {
                0%   { opacity:0; transform: translateX(110%) scale(0.88); }
                55%  { opacity:1; transform: translateX(-8px) scale(1.02); }
                78%  {            transform: translateX(4px)  scale(0.99); }
                100% {            transform: translateX(0)    scale(1);    }
            }
            @keyframes _tInM {
                0%   { opacity:0; transform: translateY(-60px) scale(0.9); }
                60%  { opacity:1; transform: translateY(5px)   scale(1.02); }
                80%  {            transform: translateY(-2px)  scale(0.99); }
                100% {            transform: translateY(0)     scale(1);    }
            }
            @keyframes _tOut {
                0%   { opacity:1; transform: translateX(0)    scale(1);    max-height:120px; padding-top:14px; padding-bottom:10px; margin-bottom:0; }
                20%  {            transform: translateX(-6px)  scale(1.01); }
                100% { opacity:0; transform: translateX(110%) scale(0.88); max-height:0;    padding-top:0;    padding-bottom:0;    margin-bottom:-10px; }
            }
            @keyframes _tOutM {
                0%   { opacity:1; transform: translateY(0)    scale(1);   max-height:120px; padding-top:14px; padding-bottom:10px; margin-bottom:0; }
                100% { opacity:0; transform: translateY(-50px) scale(0.9); max-height:0;    padding-top:0;    padding-bottom:0;    margin-bottom:-10px; }
            }
            .psyai-toast {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                border-radius: 16px;
                padding: 14px 14px 10px;
                box-shadow: 0 10px 36px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.09);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                position: relative;
                overflow: hidden;
                pointer-events: all;
                font-family: 'Nunito Sans','Segoe UI',Arial,sans-serif;
                width: 100%;
                box-sizing: border-box;
                animation: _tIn 0.52s cubic-bezier(0.22,1,0.36,1) both;
            }
            .psyai-toast.removing {
                animation: _tOut 0.38s cubic-bezier(0.55,0,0.45,1) forwards;
                pointer-events: none;
            }
            @media (max-width: 500px) {
                .psyai-toast {
                    animation-name: _tInM;
                    border-radius: 14px;
                    padding: 12px 12px 9px;
                    gap: 10px;
                }
                .psyai-toast.removing {
                    animation-name: _tOutM;
                }
            }
            .psyai-toast-icon {
                flex-shrink: 0;
                width: 38px; height: 38px;
                border-radius: 11px;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 8px;
                margin-top: 1px;
                box-sizing: border-box;
            }
            @media (max-width: 500px) {
                .psyai-toast-icon { width: 33px; height: 33px; padding: 6px; border-radius: 9px; }
            }
            .psyai-toast-body { flex: 1; min-width: 0; }
            .psyai-toast-label {
                font-size: 0.66rem;
                font-weight: 800;
                letter-spacing: 0.09em;
                text-transform: uppercase;
                margin-bottom: 3px;
                opacity: 0.72;
            }
            .psyai-toast-msg {
                font-size: 0.875rem;
                font-weight: 600;
                line-height: 1.45;
                word-break: break-word;
            }
            @media (max-width: 500px) {
                .psyai-toast-label { font-size: 0.61rem; }
                .psyai-toast-msg   { font-size: 0.82rem; }
            }
            .psyai-toast-close {
                flex-shrink: 0;
                background: none;
                border: none;
                cursor: pointer;
                opacity: 0.4;
                padding: 3px;
                line-height: 0;
                border-radius: 6px;
                transition: opacity 0.18s, background 0.18s;
                margin-top: 2px;
            }
            .psyai-toast-close:hover { opacity: 1; background: rgba(128,128,128,0.13); }
            .psyai-toast-bar {
                position: absolute;
                bottom: 0; left: 0;
                height: 3px; width: 100%;
                border-radius: 0 0 16px 16px;
                transform-origin: left;
                transform: scaleX(1);
                opacity: 0.6;
            }
        `;
        document.head.appendChild(s);
    }

    window.mostrarToast = function (mensaje, tipo = 'info', duracion = 4000) {
        const dark   = document.documentElement.classList.contains('dark-mode');
        const config = TIPOS[tipo] || TIPOS.info;
        const col    = dark ? config.dark : config.light;
        const c      = getToastContainer();

        PsyAINotifications.checkLimit();

        const toast = document.createElement('div');
        toast.className        = 'psyai-toast';
        toast.style.background = col.bg;
        toast.style.border     = `1px solid ${col.border}`;

        const icon = document.createElement('div');
        icon.className        = 'psyai-toast-icon';
        icon.style.background = col.iconBg;
        icon.style.boxShadow  = `0 4px 14px ${col.iconShadow}`;
        icon.innerHTML        = config.svg;

        const body  = document.createElement('div');
        body.className = 'psyai-toast-body';

        const lbl   = document.createElement('div');
        lbl.className   = 'psyai-toast-label';
        lbl.textContent = config.label;
        lbl.style.color = col.subtext;

        const msg   = document.createElement('div');
        msg.className   = 'psyai-toast-msg';
        msg.textContent = mensaje;
        msg.style.color = col.text;

        body.appendChild(lbl);
        body.appendChild(msg);

        const btn = document.createElement('button');
        btn.className = 'psyai-toast-close';
        btn.style.color = col.subtext;
        btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
        btn.onclick = () => removeToast(toast);

        const bar = document.createElement('div');
        bar.className        = 'psyai-toast-bar';
        bar.style.background = col.progress;
        bar.style.transition = `transform ${duracion}ms linear`;

        toast.append(icon, body, btn, bar);
        c.appendChild(toast);

        requestAnimationFrame(() => requestAnimationFrame(() => {
            bar.style.transform = 'scaleX(0)';
        }));

        let start    = Date.now();
        let left     = duracion;
        let timer    = setTimeout(() => removeToast(toast), duracion);

        toast.addEventListener('mouseenter', () => {
            clearTimeout(timer);
            left -= Date.now() - start;
            bar.style.transition = 'none';
        });
        toast.addEventListener('mouseleave', () => {
            start = Date.now();
            bar.style.transition = `transform ${left}ms linear`;
            bar.style.transform  = 'scaleX(0)';
            timer = setTimeout(() => removeToast(toast), left);
        });

        toast._timer = timer;
    };

    function removeToast(toast) {
        if (toast.classList.contains('removing')) return;
        clearTimeout(toast._timer);
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 400);
    }

})();