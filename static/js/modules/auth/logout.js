function mostrarOverlayCierreSesion(mensaje) {
  const overlayText = mensaje || 'Cerrando sesion...';
  const isDark = document.documentElement.classList.contains('dark-mode');

  const overlay = document.createElement('div');
  overlay.id = 'logout-overlay';
  overlay.innerHTML = `
    <div class="logout-overlay__card">
      <div class="logout-overlay__logo-wrap">
        <div class="logout-overlay__glow"></div>
        <div class="logout-overlay__orbit logout-overlay__orbit--1"></div>
        <div class="logout-overlay__orbit logout-overlay__orbit--2"></div>
        <div class="logout-overlay__orbit logout-overlay__orbit--3"></div>
        <div class="logout-overlay__ring-arc">
          <svg viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="54" class="logout-overlay__ring-bg"/>
            <circle cx="60" cy="60" r="54" class="logout-overlay__ring-fg"/>
          </svg>
        </div>
        <img src="/img/Logo.webp" alt="PsyAI Connect" class="logout-overlay__logo">
        <div class="logout-overlay__dot logout-overlay__dot--1"></div>
        <div class="logout-overlay__dot logout-overlay__dot--2"></div>
        <div class="logout-overlay__dot logout-overlay__dot--3"></div>
        <div class="logout-overlay__dot logout-overlay__dot--4"></div>
      </div>
      <p class="logout-overlay__text">${overlayText}</p>
      <div class="logout-overlay__progress">
        <div class="logout-overlay__progress-bar"></div>
      </div>
    </div>
  `;
  Object.assign(overlay.style, {
    position: 'fixed',
    inset: '0',
    background: isDark
      ? 'radial-gradient(ellipse at center, rgba(15,29,50,.92) 0%, rgba(3,6,16,.97) 100%)'
      : 'radial-gradient(ellipse at center, rgba(240,245,252,.88) 0%, rgba(255,255,255,.96) 100%)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: '9999',
    opacity: '0',
    transition: 'opacity .35s ease'
  });
  document.body.appendChild(overlay);
  requestAnimationFrame(() => { overlay.style.opacity = '1'; });

  const style = document.createElement('style');
  style.dataset.logoutOverlay = '';
  style.textContent = `
    .logout-overlay__card {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 32px;
      padding: 52px 60px;
      border-radius: 28px;
      background: ${isDark ? 'rgba(11,20,41,.7)' : 'rgba(255,255,255,.75)'};
      border: 1px solid ${isDark ? 'rgba(144,202,249,.1)' : 'rgba(13,71,161,.06)'};
      box-shadow: 0 8px 48px ${isDark ? 'rgba(0,0,0,.5)' : 'rgba(13,71,161,.12)'}, inset 0 1px 0 ${isDark ? 'rgba(144,202,249,.06)' : 'rgba(255,255,255,.6)'};
      animation: logout-card-in .5s cubic-bezier(.22,1,.36,1) both;
    }

    /* ── logo container ── */
    .logout-overlay__logo-wrap {
      position: relative;
      width: 140px;
      height: 140px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* ── glow halo ── */
    .logout-overlay__glow {
      position: absolute;
      inset: -18px;
      border-radius: 50%;
      background: radial-gradient(circle, ${isDark ? 'rgba(144,202,249,.18)' : 'rgba(13,71,161,.1)'} 0%, transparent 70%);
      animation: logout-glow-pulse 2.4s ease-in-out infinite;
    }

    /* ── orbiting rings ── */
    .logout-overlay__orbit {
      position: absolute;
      border-radius: 50%;
      border: 1.5px solid transparent;
    }
    .logout-overlay__orbit--1 {
      inset: -4px;
      border-top-color: #0D47A1;
      border-right-color: ${isDark ? 'rgba(144,202,249,.5)' : 'rgba(21,101,192,.4)'};
      animation: logout-orbit-spin 1.6s cubic-bezier(.4,.1,.2,1) infinite;
    }
    .logout-overlay__orbit--2 {
      inset: -12px;
      border-bottom-color: ${isDark ? '#90CAF9' : '#0D47A1'};
      border-left-color: ${isDark ? 'rgba(21,101,192,.4)' : 'rgba(144,202,249,.5)'};
      animation: logout-orbit-spin 2.4s cubic-bezier(.4,.1,.2,1) infinite reverse;
      opacity: .6;
    }
    .logout-overlay__orbit--3 {
      inset: -20px;
      border-top-color: ${isDark ? 'rgba(144,202,249,.25)' : 'rgba(13,71,161,.15)'};
      border-right-color: ${isDark ? 'rgba(144,202,249,.15)' : 'rgba(13,71,161,.08)'};
      animation: logout-orbit-spin 3.6s linear infinite;
      opacity: .4;
    }

    /* ── SVG ring arc (circular progress) ── */
    .logout-overlay__ring-arc {
      position: absolute;
      inset: -2px;
      animation: logout-orbit-spin 3s linear infinite;
    }
    .logout-overlay__ring-arc svg {
      width: 100%;
      height: 100%;
      transform: rotate(-90deg);
    }
    .logout-overlay__ring-bg {
      fill: none;
      stroke: ${isDark ? 'rgba(144,202,249,.08)' : 'rgba(13,71,161,.06)'};
      stroke-width: 2.5;
    }
    .logout-overlay__ring-fg {
      fill: none;
      stroke: url(#logout-ring-grad);
      stroke-width: 2.5;
      stroke-linecap: round;
      stroke-dasharray: 339.292;
      stroke-dashoffset: 339.292;
      animation: logout-ring-draw 2s cubic-bezier(.4,0,.2,1) forwards;
    }

    /* ── orbiting dots ── */
    .logout-overlay__dot {
      position: absolute;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #90CAF9;
    }
    .logout-overlay__dot--1 {
      top: -3px; left: 50%; transform: translateX(-50%);
      box-shadow: 0 0 8px #90CAF9, 0 0 16px rgba(144,202,249,.4);
      animation: logout-dot-orbit1 1.6s cubic-bezier(.4,.1,.2,1) infinite;
    }
    .logout-overlay__dot--2 {
      bottom: -3px; left: 50%; transform: translateX(-50%);
      background: #0D47A1;
      box-shadow: 0 0 8px #0D47A1, 0 0 16px rgba(13,71,161,.4);
      width: 5px; height: 5px;
      animation: logout-dot-orbit2 2.4s cubic-bezier(.4,.1,.2,1) infinite;
    }
    .logout-overlay__dot--3 {
      top: 50%; left: -3px; transform: translateY(-50%);
      background: ${isDark ? '#90CAF9' : '#1565C0'};
      box-shadow: 0 0 6px ${isDark ? '#90CAF9' : '#1565C0'};
      width: 4px; height: 4px;
      opacity: .7;
      animation: logout-dot-orbit3 3.6s linear infinite;
    }
    .logout-overlay__dot--4 {
      top: 50%; right: -3px; transform: translateY(-50%);
      background: #0D47A1;
      box-shadow: 0 0 6px rgba(13,71,161,.5);
      width: 4px; height: 4px;
      opacity: .5;
      animation: logout-dot-orbit4 3.6s linear infinite;
    }

    /* ── logo ── */
    .logout-overlay__logo {
      width: 100px;
      height: 100px;
      border-radius: 50%;
      object-fit: cover;
      position: relative;
      z-index: 2;
      box-shadow:
        0 0 0 3px ${isDark ? 'rgba(11,20,41,.9)' : 'rgba(255,255,255,.9)'},
        0 0 20px ${isDark ? 'rgba(144,202,249,.2)' : 'rgba(13,71,161,.12)'},
        0 0 40px ${isDark ? 'rgba(144,202,249,.1)' : 'rgba(13,71,161,.06)'};
      animation: logout-logo-breathe 2.4s ease-in-out infinite;
    }

    /* ── text ── */
    .logout-overlay__text {
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      color: ${isDark ? '#d0dde8' : '#3A526B'};
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: .3px;
      margin: 0;
      animation: logout-text-in .5s .15s ease both;
    }

    /* ── progress ── */
    .logout-overlay__progress {
      width: 200px;
      height: 4px;
      border-radius: 2px;
      background: ${isDark ? 'rgba(144,202,249,.1)' : 'rgba(13,71,161,.06)'};
      overflow: hidden;
      animation: logout-text-in .5s .25s ease both;
    }
    .logout-overlay__progress-bar {
      width: 0%;
      height: 100%;
      border-radius: 2px;
      background: linear-gradient(90deg, #0D47A1, #90CAF9, #0D47A1);
      background-size: 200% 100%;
      animation: logout-progress-fill 2s .1s cubic-bezier(.4,0,.2,1) forwards,
                 logout-progress-shimmer 1.2s linear infinite;
    }

    /* ── keyframes ── */
    @keyframes logout-card-in {
      from { opacity: 0; transform: scale(.92) translateY(12px); }
      to   { opacity: 1; transform: scale(1) translateY(0); }
    }
    @keyframes logout-text-in {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes logout-orbit-spin {
      to { transform: rotate(360deg); }
    }
    @keyframes logout-glow-pulse {
      0%, 100% { opacity: .7; transform: scale(1); }
      50%      { opacity: 1;  transform: scale(1.08); }
    }
    @keyframes logout-logo-breathe {
      0%, 100% {
        transform: scale(1);
        box-shadow: 0 0 0 3px ${isDark ? 'rgba(11,20,41,.9)' : 'rgba(255,255,255,.9)'}, 0 0 20px ${isDark ? 'rgba(144,202,249,.2)' : 'rgba(13,71,161,.12)'}, 0 0 40px ${isDark ? 'rgba(144,202,249,.1)' : 'rgba(13,71,161,.06)'};
      }
      50% {
        transform: scale(1.03);
        box-shadow: 0 0 0 3px ${isDark ? 'rgba(11,20,41,.9)' : 'rgba(255,255,255,.9)'}, 0 0 28px ${isDark ? 'rgba(144,202,249,.3)' : 'rgba(13,71,161,.18)'}, 0 0 52px ${isDark ? 'rgba(144,202,249,.15)' : 'rgba(13,71,161,.1)'};
      }
    }
    @keyframes logout-ring-draw {
      to { stroke-dashoffset: 0; }
    }
    @keyframes logout-dot-orbit1 {
      0%   { transform: translateX(-50%) rotate(0deg)   translateY(-66px) rotate(0deg); }
      100% { transform: translateX(-50%) rotate(360deg) translateY(-66px) rotate(-360deg); }
    }
    @keyframes logout-dot-orbit2 {
      0%   { transform: translateX(-50%) rotate(0deg)   translateY(66px) rotate(0deg); }
      100% { transform: translateX(-50%) rotate(360deg) translateY(66px) rotate(-360deg); }
    }
    @keyframes logout-dot-orbit3 {
      0%   { transform: translateY(-50%) rotate(0deg)   translateX(-74px) rotate(0deg); }
      100% { transform: translateY(-50%) rotate(360deg) translateX(-74px) rotate(-360deg); }
    }
    @keyframes logout-dot-orbit4 {
      0%   { transform: translateY(-50%) rotate(0deg)   translateX(74px) rotate(0deg); }
      100% { transform: translateY(-50%) rotate(360deg) translateX(74px) rotate(-360deg); }
    }
    @keyframes logout-progress-fill {
      from { width: 0%; }
      to   { width: 100%; }
    }
    @keyframes logout-progress-shimmer {
      from { background-position: 200% 0; }
      to   { background-position: -200% 0; }
    }
  `;
  document.head.appendChild(style);

  // inject SVG gradient defs into the ring
  const svgNS = 'http://www.w3.org/2000/svg';
  const defs = document.createElementNS(svgNS, 'defs');
  const grad = document.createElementNS(svgNS, 'linearGradient');
  grad.id = 'logout-ring-grad';
  grad.setAttribute('gradientUnits', 'userSpaceOnUse');
  grad.setAttribute('x1', '0'); grad.setAttribute('y1', '0');
  grad.setAttribute('x2', '120'); grad.setAttribute('y2', '120');
  const s1 = document.createElementNS(svgNS, 'stop');
  s1.setAttribute('offset', '0%'); s1.setAttribute('stop-color', '#0D47A1');
  const s2 = document.createElementNS(svgNS, 'stop');
  s2.setAttribute('offset', '50%'); s2.setAttribute('stop-color', '#90CAF9');
  const s3 = document.createElementNS(svgNS, 'stop');
  s3.setAttribute('offset', '100%'); s3.setAttribute('stop-color', '#0D47A1');
  grad.append(s1, s2, s3);
  defs.append(grad);
  const svg = overlay.querySelector('.logout-overlay__ring-arc svg');
  if (svg) svg.prepend(defs);

  return overlay;
}

async function cerrarSesion() {
  const overlay = mostrarOverlayCierreSesion();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  let serverOk = false;
  try {
    const res = await fetch('/api/logout', {
      method: 'POST',
      credentials: 'include',
      signal: controller.signal
    });
    serverOk = res.ok;
  } catch (_) {}
  clearTimeout(timeout);

  if (!serverOk) {
    if (overlay) overlay.remove();
    const style = document.querySelector('style[data-logout-overlay]');
    if (style) style.remove();
    if (typeof mostrarToast === 'function') {
      mostrarToast('No se pudo cerrar sesion. Verifica tu conexion e intenta de nuevo.', 'error');
    } else {
      alert('No se pudo cerrar sesion. Verifica tu conexion e intenta de nuevo.');
    }
    return;
  }

  try {
    localStorage.removeItem('usuario');
    localStorage.removeItem('sessionUser');
    sessionStorage.removeItem('psyai_login_return_guard');
  } catch (_) {}

  const preload = new Image();
  preload.src = '/';
  await new Promise((resolve) => setTimeout(resolve, 2000));
  window.location.href = '/';
}
