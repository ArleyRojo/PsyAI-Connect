// Política de contraseñas configurada por el admin (HU-23).
// Carga los requisitos y actualiza los textos de los formularios de registro y de nueva contraseña.
(function () {
    'use strict';
    window.PSY_POLITICA_PASS = { minimo: 6, mayuscula: true, numero: true, simbolo: false };

    window.cumplePoliticaPass = function (v) {
        var p = window.PSY_POLITICA_PASS;
        v = v || '';
        return v.length >= p.minimo &&
            (!p.mayuscula || /[A-Z]/.test(v)) &&
            (!p.numero || /[0-9]/.test(v)) &&
            (!p.simbolo || /[^A-Za-z0-9]/.test(v));
    };

    function aplicar(p) {
        var len = document.querySelector('#rule-len span');
        if (len) len.textContent = 'Mínimo ' + p.minimo + ' caracteres';
        var mostrar = { 'rule-upper': p.mayuscula, 'rule-num': p.numero, 'rule-sym': p.simbolo };
        Object.keys(mostrar).forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.style.display = mostrar[id] ? '' : 'none';
        });
        var nueva = document.getElementById('new_password');
        if (nueva) nueva.placeholder = 'Mínimo ' + p.minimo + ' caracteres';
        document.querySelectorAll('[data-politica-pass-texto]').forEach(function (el) { el.textContent = p.texto; });
    }

    fetch('/api/politicas/contrasena', { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
            if (!data || !data.success) return;
            window.PSY_POLITICA_PASS = data;
            var listo = function () { aplicar(data); };
            if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', listo);
            else listo();
        })
        .catch(function () {});
})();
