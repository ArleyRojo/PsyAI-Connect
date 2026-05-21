/* ══════════════════════════════════════════════════════
   register.js — Lógica exclusiva del formulario de registro
   PsyAI Connect
══════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════
   CAMPOS y su peso en el progreso global
   5 campos × 20% = 100%
═══════════════════════════════════════════ */
const FIELDS = [
    {
        id: 'nombre',
        check: () => document.getElementById('nombre').value.trim().length >= 2,
        step: 1
    },
    {
        id: 'email',
        check: () => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(document.getElementById('email').value.trim()),
        step: 1
    },
    {
        id: 'genero',
        check: () => document.getElementById('genero').value !== '',
        step: 1
    },
    {
        id: 'password',
        check: () => {
            const v = document.getElementById('password').value;
            return v.length >= 6 && /[A-Z]/.test(v) && /[0-9]/.test(v);
        },
        step: 2
    },
    {
        id: 'confirm-password',
        check: () => {
            const p = document.getElementById('password').value;
            const c = document.getElementById('confirm-password').value;
            return c.length > 0 && p === c;
        },
        step: 2
    }
];

const STEP_LABELS = {
    1: 'Tus datos',
    2: 'Seguridad',
    3: 'Confirmar'
};

let currentRegStep = 1;

/* ══════════════════════════════
   PROGRESO
══════════════════════════════ */
function recalcProgress() {
    const done = FIELDS.filter(f => f.check()).length;
    const pct  = Math.round((done / FIELDS.length) * 100);
    document.getElementById('regProgressFill').style.width = pct + '%';
    document.getElementById('regProgressPct').textContent  = pct + '%';
}

/* ══════════════════════════════
   STEPPER
══════════════════════════════ */
function regGoStep(n) {
    if (n > currentRegStep) {
        if (currentRegStep === 1 && !validateStep1()) return;
        if (currentRegStep === 2 && !validateStep2()) return;
    }
    if (n === 3) buildRegResumen();

    const prev = document.getElementById('regPanel' + currentRegStep);
    prev.classList.remove('active');
    prev.classList.add('leaving');
    setTimeout(() => prev.classList.remove('leaving'), 300);

    currentRegStep = n;

    const next = document.getElementById('regPanel' + n);
    next.classList.add('active');

    [1, 2, 3].forEach(i => {
        const el = document.getElementById('regStep' + i);
        el.classList.remove('active', 'done');
        if (i < n)        el.classList.add('done');
        else if (i === n) el.classList.add('active');
    });

    document.getElementById('regProgressLabel').textContent = STEP_LABELS[n];
    recalcProgress();
}

/* ══════════════════════════════
   VALIDACIONES
══════════════════════════════ */
function validateStep1() {
    const nombre = document.getElementById('nombre').value.trim();
    const email  = document.getElementById('email').value.trim();
    const genero = document.getElementById('genero').value;

    if (!nombre || nombre.length < 2) {
        mostrarToast('¿Cómo te llamamos? Ingresa tu nombre completo para continuar.', 'warning');
        return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        mostrarToast('El correo no parece válido. Usa el formato usuario@dominio.com', 'warning');
        return false;
    }
    if (!genero) {
        mostrarToast('Selecciona tu género para completar tu perfil.', 'warning');
        return false;
    }
    return true;
}

function validateStep2() {
    const pass    = document.getElementById('password').value;
    const confirm = document.getElementById('confirm-password').value;

    if (pass.length < 6) {
        mostrarToast('La contraseña es muy corta. Usa al menos 6 caracteres para proteger tu cuenta.', 'warning');
        return false;
    }
    if (!/[A-Z]/.test(pass)) {
        mostrarToast('Agrega al menos una letra mayúscula a tu contraseña.', 'warning');
        return false;
    }
    if (!/[0-9]/.test(pass)) {
        mostrarToast('Incluye al menos un número en tu contraseña.', 'warning');
        return false;
    }
    if (pass !== confirm) {
        mostrarToast('Las contraseñas no coinciden. Verifícalas antes de continuar.', 'danger');
        return false;
    }
    return true;
}

/* ══════════════════════════════
   FUERZA DE CONTRASEÑA
══════════════════════════════ */
function checkPwd() {
    const val      = document.getElementById('password').value;
    const fill     = document.getElementById('pwdFill');
    const hint     = document.getElementById('pwdHint');
    const hasLen   = val.length >= 6;
    const hasUpper = /[A-Z]/.test(val);
    const hasNum   = /[0-9]/.test(val);
    const hasSpec  = /[^A-Za-z0-9]/.test(val);

    const setRule = (id, ok) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.toggle('ok', ok);
        el.querySelector('i').className = ok ? 'fas fa-check-circle' : 'fas fa-circle';
    };
    setRule('rule-len',   hasLen);
    setRule('rule-upper', hasUpper);
    setRule('rule-num',   hasNum);

    let score = 0;
    if (hasLen)   score++;
    if (hasUpper) score++;
    if (hasNum)   score++;
    if (hasSpec)  score++;

    const widths = ['0%', '28%', '54%', '78%', '100%'];
    const colors = ['', '#ef5350', '#ffa726', '#66bb6a', '#43a047'];
    const labels = ['', 'Muy débil', 'Regular', 'Buena', 'Excelente'];

    fill.style.width      = widths[score];
    fill.style.background = colors[score];
    hint.textContent      = score > 0 ? labels[score] : '';
    hint.style.color      = colors[score] || 'inherit';
}

/* ══════════════════════════════
   RESUMEN PASO 3
══════════════════════════════ */
function buildRegResumen() {
    const nombre = document.getElementById('nombre').value.trim() || '—';
    const email  = document.getElementById('email').value.trim()  || '—';
    const genero = document.getElementById('genero').value        || '—';
    document.getElementById('regResumen').innerHTML = `
        <div style="display:grid;gap:6px;">
            <div><strong>Nombre:</strong> ${nombre}</div>
            <div><strong>Correo:</strong> ${email}</div>
            <div><strong>Género:</strong> ${genero}</div>
        </div>`;
}   

/* ══════════════════════════════
   SUBMIT
══════════════════════════════ */
async function submitRegister() {
    const nombre           = document.getElementById('nombre').value.trim();
    const email            = document.getElementById('email').value.trim();
    const genero           = document.getElementById('genero').value;
    const password         = document.getElementById('password').value;
    const confirm_password = document.getElementById('confirm-password').value;

    const btn = document.getElementById('btnRegistrar');
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Creando cuenta...';

    try {
        const res  = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ nombre, email, genero, password, confirm_password })
        });
        const data = await res.json();

        if (data.success) {
            mostrarToast('¡Bienvenido/a a PsyAI Connect! Redirigiendo al inicio de sesión...', 'success');
            setTimeout(() => { window.location.href = 'login.html'; }, 1500);
        } else {
            if (res.status === 409)
                mostrarToast('Este correo ya tiene una cuenta registrada. ¿Olvidaste tu contraseña?', 'danger');
            else if (res.status === 400)
                mostrarToast(data.message || 'Algunos datos no son válidos. Revisa los campos e intenta de nuevo.', 'warning');
            else
                mostrarToast(data.message || 'No se pudo crear tu cuenta. Inténtalo en unos momentos.', 'danger');

            btn.disabled  = false;
            btn.innerHTML = '<i class="fas fa-user-plus me-1"></i> Crear cuenta';
        }
    } catch {
        mostrarToast('Sin conexión con el servidor. Verifica tu internet e intenta de nuevo.', 'danger');
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-user-plus me-1"></i> Crear cuenta';
    }
}


/* ══════════════════════════════
   MOSTRAR / OCULTAR CONTRASEÑA
══════════════════════════════ */
function togglePwd(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon  = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
        btn.setAttribute('aria-label', 'Ocultar contraseña');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
        btn.setAttribute('aria-label', 'Mostrar contraseña');
    }
}

/* ══════════════════════════════
   PARTÍCULAS FLOTANTES
══════════════════════════════ */
(function () {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W = 0, H = 0;

    const LIGHT = [[144,202,249],[100,181,246],[179,229,252],[33,150,243],[207,226,255],[66,165,245],[21,101,192]];
    const DARK  = [[74,134,240],[30,80,160],[15,52,120],[100,160,255],[50,110,210],[20,70,180],[10,40,100]];

    function isDark() { return document.documentElement.classList.contains('dark-mode'); }
    function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }

    function mkParticle(startY) {
        const pal = isDark() ? DARK : LIGHT;
        const c   = pal[Math.floor(Math.random() * pal.length)];
        const op  = isDark() ? (0.22 + Math.random() * 0.32) : (0.30 + Math.random() * 0.38);
        const r   = 5 + Math.random() * 18;
        return {
            x: 10 + Math.random() * Math.max(W - 20, 100),
            y: startY !== undefined ? startY : H + r,
            r,
            vx: (Math.random() - 0.5) * 0.5,
            vy: -(0.35 + Math.random() * 0.65),
            color: `rgba(${c[0]},${c[1]},${c[2]},${op.toFixed(2)})`
        };
    }

    let particles = [];
    function init() {
        resize();
        particles = [];
        for (let i = 0; i < 45; i++) particles.push(mkParticle(Math.random() * H));
    }
    function recolor() {
        const pal = isDark() ? DARK : LIGHT;
        particles.forEach(p => {
            const c  = pal[Math.floor(Math.random() * pal.length)];
            const op = isDark() ? (0.22 + Math.random() * 0.32) : (0.30 + Math.random() * 0.38);
            p.color  = `rgba(${c[0]},${c[1]},${c[2]},${op.toFixed(2)})`;
        });
    }
    function draw() {
        ctx.clearRect(0, 0, W, H);
        particles.forEach(p => {
            p.x += p.vx; p.y += p.vy;
            if (p.y + p.r < 0) { Object.assign(p, mkParticle(H + p.r)); p.x = 10 + Math.random() * (W - 20); }
            if (p.x - p.r < 0) { p.x = p.r;     p.vx *= -1; }
            if (p.x + p.r > W) { p.x = W - p.r; p.vx *= -1; }
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();
        });
        requestAnimationFrame(draw);
    }

    new MutationObserver(recolor).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    window.addEventListener('resize', resize);
    init();
    draw();
})();

/* ══════════════════════════════
   LÍNEAS ANIMADAS EN LA CARD
══════════════════════════════ */
(function () {
    function isDark() { return document.documentElement.classList.contains('dark-mode'); }

    function getColors() {
        if (isDark()) return [
            { color: '#7c3aed', width: 2.5, dur: 3.2, offset: 0 },
            { color: '#60a5fa', width: 1.5, dur: 4.5, offset: 0.45 },
            { color: '#a78bfa', width: 1.5, dur: 3.8, offset: 0.72 },
        ];
        return [
            { color: '#0D47A1', width: 2.5, dur: 3.2, offset: 0 },
            { color: '#90CAF9', width: 1.5, dur: 4.5, offset: 0.45 },
            { color: '#1565C0', width: 1.5, dur: 3.8, offset: 0.72 },
        ];
    }

    function buildSVG(W, H) {
        const R = 32, pad = 3;
        const path = `M ${R+pad},${pad} H ${W-R-pad} A ${R},${R} 0 0 1 ${W-pad},${R+pad} V ${H-R-pad} A ${R},${R} 0 0 1 ${W-R-pad},${H-pad} H ${R+pad} A ${R},${R} 0 0 1 ${pad},${H-R-pad} V ${R+pad} A ${R},${R} 0 0 1 ${R+pad},${pad} Z`;
        const perim = 2 * (W + H) - (8 - 2 * Math.PI) * R;
        const ns  = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('class', 'card-lines-svg');
        svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:20;overflow:visible;';

        getColors().forEach(({ color, width, dur, offset }) => {
            const line = document.createElementNS(ns, 'path');
            line.setAttribute('d', path);
            line.setAttribute('fill', 'none');
            line.setAttribute('stroke', color);
            line.setAttribute('stroke-width', width);
            line.setAttribute('stroke-linecap', 'round');

            const dash  = perim * 0.18, gap = perim * 0.82, start = perim * offset;
            line.setAttribute('stroke-dasharray', `${dash} ${gap}`);
            line.setAttribute('stroke-dashoffset', `${-start}`);

            const anim = document.createElementNS(ns, 'animate');
            anim.setAttribute('attributeName', 'stroke-dashoffset');
            anim.setAttribute('from', `${-start}`);
            anim.setAttribute('to', `${-start - perim}`);
            anim.setAttribute('dur', `${dur}s`);
            anim.setAttribute('repeatCount', 'indefinite');
            anim.setAttribute('calcMode', 'linear');
            line.appendChild(anim);
            svg.appendChild(line);
        });
        return svg;
    }

    function attach() {
        const card = document.querySelector('.login-card');
        if (!card) return;
        const old = card.querySelector('.card-lines-svg');
        if (old) old.remove();
        const svg = buildSVG(card.offsetWidth, card.offsetHeight);
        card.appendChild(svg);
    }

    new MutationObserver(attach).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', attach);
    else attach();
    window.addEventListener('load', attach);
    window.addEventListener('resize', () => setTimeout(attach, 100));
    const observer = new MutationObserver(() => setTimeout(attach, 50));
document.addEventListener('DOMContentLoaded', function() {
    observer.observe(document.querySelector('.reg-panels-wrap'), { 
        childList: true, 
        subtree: true, 
        attributes: true, 
        attributeFilter: ['class'] 
    });
});
})();

/* ── Inicializar progreso al cargar ── */
document.addEventListener('DOMContentLoaded', recalcProgress);
