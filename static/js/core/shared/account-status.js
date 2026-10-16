// ============================================================
// account-status.js  — Manejo global de cuenta suspendida
// ============================================================
(function () {
  const SUSPEND_MESSAGE = "Tu cuenta ha sido suspendida. Contacta al administrador.";

  // Helper para mostrar alerta y redirigir
  function handleSuspended(responseOrMessage) {
    // Si es un mensaje string, usarlo; si es objeto con code
    var msg = SUSPEND_MESSAGE;
    if (typeof responseOrMessage === "string") {
      msg = responseOrMessage;
    } else if (responseOrMessage && responseOrMessage.message) {
      msg = responseOrMessage.message;
    }

    // Mostrar con PsyAIAlerts si disponible
    if (window.PsyAIAlerts && typeof window.PsyAIAlerts.error === "function") {
      window.PsyAIAlerts.error(msg);
    } else {
      // fallback simple
      alert(msg);
    }

    // Redirigir a login con flag
    setTimeout(function () {
      window.location.href = "/login.html?suspendida=1";
    }, 1500);
  }

  // 1) Interceptar fetch globalmente
  if (typeof fetch !== "undefined") {
    var originalFetch = window.fetch;
    window.fetch = function (url, options) {
      return originalFetch.apply(this, arguments).then(function (response) {
        // Solo nos importan respuestas 403 con code account_suspended
        if (response.status === 403) {
          var ct = response.headers.get("content-type") || "";
          if (ct.indexOf("application/json") !== -1) {
            // clonar para leer json sin consumir el stream original
            var cloned = response.clone();
            cloned.json().then(function (data) {
              if (data && data.code === "account_suspended") {
                handleSuspended(data);
              }
            }).catch(function () {
              // ignore parse errors
            });
          }
        }
        return response;
      });
    };
  }

  // 2) Escuchar eventos SSE account_suspended
  // Buscar EventSource existentes? Simpler: monkey-patch EventSource constructor
  if (typeof EventSource !== "undefined") {
    var OriginalEventSource = window.EventSource;
    window.EventSource = function (url, options) {
      var es = new OriginalEventSource(url, options);
      es.addEventListener("account_suspended", function (e) {
        try {
          var data = JSON.parse(e.data);
          handleSuspended(data);
        } catch (_) {
          handleSuspended();
        }
      });
      return es;
    };
    window.EventSource.prototype = OriginalEventSource.prototype;
  }

  // 3) En login.html, si viene ?suspendida=1 mostrar mensaje al cargar
  document.addEventListener("DOMContentLoaded", function () {
    var params = new URLSearchParams(window.location.search);
    if (params.get("suspendida") === "1") {
      if (window.PsyAIAlerts && typeof window.PsyAIAlerts.error === "function") {
        window.PsyAIAlerts.error(SUSPEND_MESSAGE);
      } else {
        alert(SUSPEND_MESSAGE);
      }
      // limpiar query param para que no vuelva a mostrar al recargar
      var cleanUrl = window.location.pathname;
      history.replaceState({}, document.title, cleanUrl);
    }
  });
})();