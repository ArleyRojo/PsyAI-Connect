// ============================================================
// inactividad.js — Cierre automático de sesión por inactividad (HU-13)
// - Cuenta el tiempo sin actividad (mouse, teclado, toques, scroll).
// - 1 minuto antes muestra un aviso con cuenta regresiva y "Seguir conectado".
// - Al llegar al límite cierra la sesión y lleva al login con un mensaje.
// - Las pestañas abiertas comparten la última actividad (localStorage).
// - Los minutos los define el administrador (página Seguridad). El admin no aplica.
// ============================================================
(function () {
  'use strict';
  if (window.__psyaiInactividad) return;
  window.__psyaiInactividad = true;

  var CLAVE_ACTIVIDAD = 'psyai_ultima_actividad';
  var MENSAJE = 'Tu sesión se cerró por inactividad. Vuelve a iniciar sesión.';
  var PING_CADA_MS = 2 * 60 * 1000; // avisar al servidor que seguimos activos

  var limiteMs = 15 * 60 * 1000;
  var avisoMs = 60 * 1000;
  var ultimaLocal = Date.now();
  var ultimoPing = Date.now();
  var avisoVisible = false;
  var cerrando = false;
  var intervalo = null;
  var aviso = null;

  function leer(clave) {
    try { return localStorage.getItem(clave); } catch (_) { return null; }
  }

  function escribir(clave, valor) {
    try { localStorage.setItem(clave, valor); } catch (_) {}
  }

  function esPaginaDeLogin() {
    return /\/(login\.html|auth\/login)/.test(window.location.pathname);
  }

  function esPaginaPrivada() {
    var p = window.location.pathname;
    return p.indexOf('/aside-patient/') === 0 || p.indexOf('/aside-professional/') === 0 ||
      p === '/patient.dashboard.html' || p === '/professional.dashboard.html';
  }

  // ── Mensaje en el login ────────────────────────────────────
  function mostrarMensajeEnLogin() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('inactividad') !== '1') return;
    setTimeout(function () {
      // alerts.js declara PsyAIAlerts con const, por eso no siempre está en window
      var alertas = window.PsyAIAlerts || (typeof PsyAIAlerts !== 'undefined' ? PsyAIAlerts : null);
      if (alertas && typeof alertas.warning === 'function') {
        alertas.warning(MENSAJE, 'Sesión cerrada');
      } else {
        var caja = document.createElement('div');
        caja.setAttribute('role', 'status');
        caja.textContent = MENSAJE;
        caja.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:30000;' +
          'padding:12px 18px;border-radius:10px;background:#fef3c7;color:#92400e;font-weight:600;' +
          'box-shadow:0 8px 24px rgba(0,0,0,.15)';
        document.body.appendChild(caja);
        setTimeout(function () { caja.remove(); }, 8000);
      }
    }, 300);
    history.replaceState({}, document.title, window.location.pathname);
  }

  // ── Actividad ──────────────────────────────────────────────
  function ultimaActividad() {
    var compartida = Number(leer(CLAVE_ACTIVIDAD)) || 0;
    return Math.max(compartida, ultimaLocal);
  }

  function registrarActividad() {
    if (avisoVisible || cerrando) return; // con el aviso abierto hay que usar el botón
    var ahora = Date.now();
    if (ahora - ultimaLocal < 1000) return;
    ultimaLocal = ahora;
    escribir(CLAVE_ACTIVIDAD, String(ahora));
    if (ahora - ultimoPing > PING_CADA_MS) pingServidor();
  }

  function pingServidor() {
    ultimoPing = Date.now();
    return fetch('/api/sesion/inactividad', { credentials: 'include' })
      .then(function (r) {
        if (r.status === 401) { irAlLogin(); return null; }
        return r.ok ? r.json() : null;
      })
      .then(function (data) { if (data) aplicarConfig(data); })
      .catch(function () {});
  }

  function aplicarConfig(data) {
    limiteMs = Math.max(1, Number(data.minutos) || 15) * 60 * 1000;
    avisoMs = Math.min((Number(data.avisoSegundos) || 60) * 1000, limiteMs / 2);
  }

  // ── Aviso ──────────────────────────────────────────────────
  function crearAviso() {
    var estilo = document.createElement('style');
    estilo.textContent = [
      '.inactividad-fondo{position:fixed;inset:0;z-index:30000;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(15,23,42,.55);backdrop-filter:blur(4px)}',
      '.inactividad-caja{width:min(400px,100%);padding:28px 24px;border-radius:18px;background:#fff;color:#1e293b;text-align:center;box-shadow:0 20px 50px rgba(15,23,42,.3);font-family:inherit}',
      '.inactividad-icono{width:56px;height:56px;margin:0 auto 12px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#fef3c7;color:#b45309;font-size:24px}',
      '.inactividad-caja h2{margin:0 0 6px;font-size:1.15rem;font-weight:700}',
      '.inactividad-caja p{margin:0 0 18px;color:#64748b;font-size:.92rem}',
      '.inactividad-cuenta{font-size:2.2rem;font-weight:800;color:#b45309;margin:4px 0 14px}',
      '.inactividad-botones{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}',
      '.inactividad-btn{border:0;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit}',
      '.inactividad-btn--seguir{background:#1565c0;color:#fff}',
      '.inactividad-btn--salir{background:#e2e8f0;color:#1e293b}',
      'html.dark-mode .inactividad-caja{background:#0b1429;color:#e8f0f8;border:1px solid #243352}',
      'html.dark-mode .inactividad-caja p{color:#8aa0bc}',
      'html.dark-mode .inactividad-icono{background:rgba(245,158,11,.18);color:#fbbf24}',
      'html.dark-mode .inactividad-cuenta{color:#fbbf24}',
      'html.dark-mode .inactividad-btn--salir{background:#132843;color:#d0dde8}'
    ].join('');
    document.head.appendChild(estilo);

    aviso = document.createElement('div');
    aviso.className = 'inactividad-fondo';
    aviso.hidden = true;
    aviso.setAttribute('role', 'alertdialog');
    aviso.setAttribute('aria-modal', 'true');
    aviso.setAttribute('aria-labelledby', 'inactividadTitulo');
    aviso.innerHTML =
      '<div class="inactividad-caja">' +
        '<div class="inactividad-icono"><i class="fas fa-hourglass-half"></i></div>' +
        '<h2 id="inactividadTitulo">¿Sigues ahí?</h2>' +
        '<p>Por tu seguridad, tu sesión se cerrará por inactividad en</p>' +
        '<div class="inactividad-cuenta" id="inactividadCuenta">60 s</div>' +
        '<div class="inactividad-botones">' +
          '<button type="button" class="inactividad-btn inactividad-btn--salir" id="inactividadSalir">Cerrar sesión</button>' +
          '<button type="button" class="inactividad-btn inactividad-btn--seguir" id="inactividadSeguir">Seguir conectado</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(aviso);

    document.getElementById('inactividadSeguir').addEventListener('click', seguirConectado);
    document.getElementById('inactividadSalir').addEventListener('click', function () { cerrarSesion(false); });
  }

  function mostrarAviso(restanteMs) {
    if (!aviso) crearAviso();
    document.getElementById('inactividadCuenta').textContent = Math.max(0, Math.ceil(restanteMs / 1000)) + ' s';
    if (!avisoVisible) {
      avisoVisible = true;
      aviso.hidden = false;
      document.getElementById('inactividadSeguir').focus();
    }
  }

  function ocultarAviso() {
    if (!avisoVisible) return;
    avisoVisible = false;
    if (aviso) aviso.hidden = true;
  }

  function seguirConectado() {
    ocultarAviso();
    ultimaLocal = Date.now();
    escribir(CLAVE_ACTIVIDAD, String(ultimaLocal));
    pingServidor();
  }

  // ── Cierre ─────────────────────────────────────────────────
  function irAlLogin() {
    if (intervalo) clearInterval(intervalo);
    try {
      localStorage.removeItem('usuario');
      localStorage.removeItem('sessionUser');
    } catch (_) {}
    window.location.href = '/login.html?inactividad=1';
  }

  function cerrarSesion(porInactividad) {
    if (cerrando) return;
    cerrando = true;
    if (intervalo) clearInterval(intervalo);
    fetch('/api/logout', { method: 'POST', credentials: 'include' })
      .catch(function () {})
      .then(function () {
        if (porInactividad) {
          irAlLogin();
        } else {
          try {
            localStorage.removeItem('usuario');
            localStorage.removeItem('sessionUser');
          } catch (_) {}
          window.location.href = '/login.html';
        }
      });
  }

  function revisar() {
    var inactivoMs = Date.now() - ultimaActividad();
    if (inactivoMs >= limiteMs) {
      cerrarSesion(true);
    } else if (inactivoMs >= limiteMs - avisoMs) {
      mostrarAviso(limiteMs - inactivoMs);
    } else {
      ocultarAviso(); // otra pestaña tuvo actividad
    }
  }

  // ── Inicio ─────────────────────────────────────────────────
  function iniciar() {
    if (esPaginaDeLogin()) { mostrarMensajeEnLogin(); return; }
    if (!esPaginaPrivada()) return;

    fetch('/api/sesion/inactividad', { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.aplica) return;
        aplicarConfig(data);
        ultimaLocal = Date.now();
        escribir(CLAVE_ACTIVIDAD, String(ultimaLocal));
        ['mousemove', 'mousedown', 'keydown', 'wheel', 'scroll', 'touchstart'].forEach(function (evento) {
          window.addEventListener(evento, registrarActividad, { passive: true, capture: true });
        });
        intervalo = setInterval(revisar, 1000);
      })
      .catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }

  // Para pruebas desde la consola: PsyAIInactividad.estado()
  window.PsyAIInactividad = {
    estado: function () {
      return { limiteSegundos: limiteMs / 1000, inactivoSegundos: Math.round((Date.now() - ultimaActividad()) / 1000) };
    }
  };
})();
