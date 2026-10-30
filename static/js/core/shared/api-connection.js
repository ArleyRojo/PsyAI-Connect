/**
 * PsyAIConnection - Wrapper centralizado de fetch para la API
 * Maneja: CSRF, timeouts, reintentos, 401/403, redirección a login
 *
 * CONTRATO DE LA API:
 * - Todos los métodos (fetchConTimeout, get, post, put, patch, del) resuelven con el JSON YA PARSEADO (objeto plano).
 * - En caso de error HTTP (4xx, 5xx, timeout, red), rechazan con un objeto: { status: number, message: string, isCsrf?: boolean }.
 * - NO llames .json(), .ok, .status sobre el resultado; ya es el dato parseado.
 * - En 401: limpia sesión local y redirige a /login.html (salvo endpoints de auth).
 * - En 403 por CSRF: refresca token automáticamente y reintenta UNA vez.
 * - En 408 (timeout): rechaza con { status: 408, message: 'Tiempo de espera agotado' }.
 * - El token CSRF se obtiene automáticamente de /api/csrf/ al cargar la página.
 */
(function () {
    'use strict';

    var csrfToken = null;
    var csrfFetched = false;
    var csrfFetching = false;
    var csrfWaiters = [];

    // ============================================================
    // CSRF Token Management
    // ============================================================

    function getCsrfTokenFromMeta() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta && meta.content ? meta.content : null;
    }

    function getCsrfTokenFromCookie() {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function setCsrfToken(token) {
        if (!token) return;
        csrfToken = token;
        csrfFetched = true;
        // Resolver todas las promesas en espera
        csrfWaiters.forEach(function (resolve) { resolve(token); });
        csrfWaiters = [];
    }

    function fetchCsrfToken() {
        if (csrfFetched || csrfFetching) {
            return Promise.resolve(csrfToken);
        }
        csrfFetching = true;

        return fetch('/api/csrf/', {
            method: 'GET',
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
        })
            .then(function (res) {
                if (!res.ok) throw new Error('CSRF endpoint ' + res.status);
                return res.json();
            })
            .then(function (data) {
                setCsrfToken(data.csrfToken);
                return csrfToken;
            })
            .catch(function (err) {
                console.warn('[PsyAIConnection] No se pudo obtener token CSRF:', err);
                // Fallback a meta tag o cookie
                var fallback = getCsrfTokenFromMeta() || getCsrfTokenFromCookie();
                if (fallback) setCsrfToken(fallback);
                return csrfToken;
            })
            .finally(function () {
                csrfFetching = false;
            });
    }

    function waitForCsrfToken() {
        if (csrfFetched) return Promise.resolve(csrfToken);
        return new Promise(function (resolve) {
            csrfWaiters.push(resolve);
            // Trigger fetch if not already
            if (!csrfFetching) fetchCsrfToken();
        });
    }

    // ============================================================
    // Core fetch wrapper
    // ============================================================

    function buildHeaders(options, csrf) {
        var headers = new Headers(options.headers || {});
        if (!headers.has('Accept')) headers.set('Accept', 'application/json');
        if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json');
        }
        if (csrf) headers.set('X-CSRFToken', csrf);
        return headers;
    }

    function handleResponse(res, url, options, csrf, retryCount) {
        // Helper to safely parse JSON
        function safeJson(res) {
            return res.json().catch(function () {
                // If JSON parsing fails, return empty object
                return {};
            });
        }

        // 401 = no autenticado (sesión expirada o no iniciada)
        if (res.status === 401) {
            // Limpiar sesión local
            try { localStorage.removeItem('usuario'); localStorage.removeItem('sessionUser'); } catch (_) { }
            // Redirigir a login si no es una petición de auth
            if (!/\/api\/(login|register|csrf|forgot-password|reset-password|verify-email)(?:\/|$)/.test(url)) {
                window.location.href = '/login.html';
            }
            return Promise.reject({ status: 401, message: 'Sesión expirada. Redirigiendo al login...' });
        }

        // 403 = puede ser CSRF o permisos
        if (res.status === 403) {
            return safeJson(res).then(function (data) {
                var msg = (data && data.message) || 'Acceso denegado';
                var isCsrf = /csrf|token/i.test(msg);
                if (isCsrf && retryCount === 0) {
                    // Token CSRF puede haber expirado - refrescar y reintentar UNA vez
                    console.warn('[PsyAIConnection] Posible CSRF expirado, refrescando token y reintentando...');
                    csrfFetched = false;
                    csrfToken = null;
                    return fetchCsrfToken().then(function (newToken) {
                        return fetchWithTimeout(url, options, retryCount + 1);
                    });
                }
                return Promise.reject({ status: 403, message: msg, isCsrf: isCsrf });
            });
        }

        // Otros errores
        if (!res.ok) {
            return safeJson(res).then(function (data) {
                var msg = (data && data.message) || ('Error ' + res.status);
                return Promise.reject({ status: res.status, message: msg });
            });
        }

        // 200 OK - parse JSON safely
        return safeJson(res);
    }

    function fetchWithTimeout(url, options, retryCount) {
        retryCount = retryCount || 0;
        var timeout = options.timeout || 15000;
        var controller = new AbortController();
        var timeoutId = setTimeout(function () { controller.abort(); }, timeout);

        var fetchOptions = {
            method: options.method || 'GET',
            headers: options.headers,
            body: options.body,
            credentials: 'include',
            signal: controller.signal
        };

        return fetch(url, fetchOptions)
            .then(function (res) {
                clearTimeout(timeoutId);
                return handleResponse(res, url, options, options.headers?.get('X-CSRFToken'), retryCount);
            })
            .catch(function (err) {
                clearTimeout(timeoutId);
                if (err.name === 'AbortError') {
                    return Promise.reject({ status: 408, message: 'Tiempo de espera agotado' });
                }
                throw err;
            });
    }

    // ============================================================
    // Public API
    // ============================================================

    window.PsyAIConnection = {
        // Obtiene el token CSRF actual (o lo busca si no lo tiene)
        getCsrfToken: function () {
            return waitForCsrfToken();
        },

        // Fuerza refresco del token CSRF
        refreshCsrfToken: function () {
            csrfFetched = false;
            csrfToken = null;
            return fetchCsrfToken();
        },

        // Fetch con timeout, CSRF automático y manejo de 401/403
        fetchConTimeout: function (url, options, timeout) {
            var opts = options || {};
            if (timeout) opts.timeout = timeout;

            // Métodos que requieren CSRF
            var method = (opts.method || 'GET').toUpperCase();
            var needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) !== -1;

            if (!needsCsrf) {
                // GET/HEAD/OPTIONS - sin CSRF
                return fetchWithTimeout(url, opts, 0);
            }

            // Requiere CSRF - esperar token y enviar
            return waitForCsrfToken().then(function (token) {
                opts.headers = buildHeaders(opts, token);
                return fetchWithTimeout(url, opts, 0);
            });
        },

        // Helpers de conveniencia
        get: function (url, opts) { return this.fetchConTimeout(url, Object.assign({ method: 'GET' }, opts)); },
        post: function (url, body, opts) {
            var o = Object.assign({ method: 'POST' }, opts);
            if (body && !(body instanceof FormData) && !o.headers?.['Content-Type']) {
                o.body = JSON.stringify(body);
            } else if (body instanceof FormData) {
                o.body = body;
            } else {
                o.body = body;
            }
            return this.fetchConTimeout(url, o);
        },
        put: function (url, body, opts) {
            var o = Object.assign({ method: 'PUT' }, opts);
            if (body && !(body instanceof FormData)) o.body = JSON.stringify(body);
            return this.fetchConTimeout(url, o);
        },
        patch: function (url, body, opts) {
            var o = Object.assign({ method: 'PATCH' }, opts);
            if (body && !(body instanceof FormData)) o.body = JSON.stringify(body);
            return this.fetchConTimeout(url, o);
        },
        del: function (url, opts) { return this.fetchConTimeout(url, Object.assign({ method: 'DELETE' }, opts)); },

        // Para mostrar errores de chatbot con botón Reintentar
        showChatbotError: function (originalMessage, onRetry) {
            if (window.Swal) {
                window.Swal.fire({
                    title: 'Error de conexión',
                    html: 'No hay conexión con el asistente en este momento.<br><small>' + originalMessage + '</small>',
                    icon: 'error',
                    showCancelButton: true,
                    confirmButtonText: 'Reintentar',
                    cancelButtonText: 'Cerrar',
                    reverseButtons: true,
                    customClass: {
                        confirmButton: 'btn btn-primary',
                        cancelButton: 'btn btn-outline-secondary'
                    },
                    buttonsStyling: false
                }).then(function (result) {
                    if (result.isConfirmed && onRetry) onRetry(originalMessage);
                });
            } else {
                // Fallback si SweetAlert no está cargado
                if (confirm('No hay conexión con el asistente. ¿Reintentar?')) {
                    if (onRetry) onRetry(originalMessage);
                }
            }
        }
    };

    // Pre-cargar token CSRF al cargar la página
    document.addEventListener('DOMContentLoaded', function () {
        fetchCsrfToken();
    });

})();