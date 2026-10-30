let _userChart = null;
let _activityChart = null;
let _realtimeChart = null;
const REALTIME_POINTS = 30;

function initCharts(stats) {
    initUserDoughnut(stats);
    initActivityBar(stats);
    initRealtimeLine(stats);
}

function initUserDoughnut(stats) {
    const ctx = document.getElementById('chartUsers');
    if (!ctx) return;
    if (_userChart) { _userChart.destroy(); }
    const activos = stats.usuarios_activos || 0;
    const total = stats.total_usuarios || 0;
    const suspendidos = stats.cuentas_suspendidas || 0;
    const otros = Math.max(0, total - activos - suspendidos);
    _userChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Activos', 'Suspendidos', 'Otros'],
            datasets: [{
                data: [activos, suspendidos, otros],
                backgroundColor: ['#4CAF50', '#f44336', '#BDBDBD'],
                borderWidth: 2,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '65%',
        }
    });
}

function initActivityBar(stats) {
    const ctx = document.getElementById('chartActivity');
    if (!ctx) return;
    if (_activityChart) { _activityChart.destroy(); }
    _activityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Visitas Hoy', 'Logs Hoy', 'Notificaciones', 'Req/min', 'Citas Pend.'],
            datasets: [{
                label: 'Cantidad',
                data: [
                    stats.visitas_hoy || 0,
                    stats.logs_hoy || 0,
                    stats.notificaciones || 0,
                    stats.requests_minuto || 0,
                    stats.citas_pendientes || 0,
                ],
                backgroundColor: [
                    'rgba(33, 150, 243, 0.7)',
                    'rgba(76, 175, 80, 0.7)',
                    'rgba(255, 152, 0, 0.7)',
                    'rgba(156, 39, 176, 0.7)',
                    'rgba(244, 67, 54, 0.7)',
                ],
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

// Historial propio: cada muestra es {t, cpu, ram, rps}. El gráfico se reconstruye
// siempre desde aquí, así que nunca queda con un solo punto ni con rellenos falsos.
const _rtHistory = [];
const RT_COLORS = { cpu: '#42A5F5', ram: '#66BB6A', rps: '#FFA726' };

function _rtNum(v, fallback) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
}

let _rtLastPush = 0;
let _rtFallbackTimer = null;

function _rtPushSample(stats) {
    _rtLastPush = Date.now();
    const last = _rtHistory.at(-1) || { cpu: 0, ram: 0, rps: 0 };
    _rtHistory.push({
        t: new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        cpu: _rtNum(stats.cpu, last.cpu),
        ram: _rtNum(stats.ram, last.ram),
        rps: _rtNum(stats.requests_minuto, last.rps),
    });
    while (_rtHistory.length > REALTIME_POINTS) _rtHistory.shift();
}

// Rango con zoom automático: nunca menor a `minSpan` para que no se aplaste.
function _rtRange(values, minSpan, hardMax) {
    let lo = Math.min(...values), hi = Math.max(...values);
    if (hi - lo < minSpan) { const mid = (hi + lo) / 2; lo = mid - minSpan / 2; hi = mid + minSpan / 2; }
    const pad = (hi - lo) * 0.15;
    lo = Math.max(0, lo - pad);
    hi = Math.min(hardMax, hi + pad);
    if (hi - lo < minSpan) hi = Math.min(hardMax, lo + minSpan);
    return { min: Math.floor(lo), max: Math.ceil(hi) };
}

function _rtLastPointRadius(n, r) {
    return Array.from({ length: n }, (_, i) => (i === n - 1 ? r : 0));
}

function _rtApply() {
    if (!_realtimeChart) return;
    const h = _rtHistory;
    const n = h.length;
    const cpu = h.map(x => x.cpu), ram = h.map(x => x.ram), rps = h.map(x => x.rps);
    const c = _realtimeChart;

    c.data.labels = h.map(x => x.t);
    [cpu, ram, rps].forEach((arr, i) => {
        c.data.datasets[i].data = arr;
        c.data.datasets[i].pointRadius = _rtLastPointRadius(n, 4);
    });
    c.data.datasets[0].label = `CPU % ${cpu.at(-1).toFixed(1)}%`;
    c.data.datasets[1].label = `RAM % ${ram.at(-1).toFixed(1)}%`;
    c.data.datasets[2].label = `Req/min ${rps.at(-1)} req/min`;

    const rc = _rtRange(cpu, 10, 100);
    const rr = _rtRange(ram, 10, 100);
    c.options.scales.y.min = rc.min;  c.options.scales.y.max = rc.max;
    c.options.scales.y2.min = rr.min; c.options.scales.y2.max = rr.max;
    c.options.scales.y1.suggestedMax = Math.max(10, Math.ceil(Math.max(...rps) * 1.3));
    c.update();
}

function initRealtimeLine(stats) {
    const ctx = document.getElementById('chartRealtime');
    if (!ctx) return;
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded');
        return;
    }
    if (_realtimeChart) { _realtimeChart.destroy(); _realtimeChart = null; }
    if (_rtHistory.length === 0) _rtPushSample(stats || {});

    const base = { tension: 0.4, borderWidth: 2.5, pointHoverRadius: 5, spanGaps: true };
    // Colores tomados del tema actual (claro u oscuro) para que siempre se lean.
    const tick = getComputedStyle(ctx.parentElement || document.body).color || '#888';
    const grid = 'rgba(128,128,128,.22)';
    _realtimeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                { ...base, label: 'CPU %', data: [], yAxisID: 'y', borderColor: RT_COLORS.cpu,
                  backgroundColor: 'rgba(66,165,245,.08)', fill: true,
                  pointBackgroundColor: RT_COLORS.cpu },
                { ...base, label: 'RAM %', data: [], yAxisID: 'y2', borderColor: RT_COLORS.ram,
                  fill: false, pointBackgroundColor: RT_COLORS.ram },
                { ...base, label: 'Req/min', data: [], yAxisID: 'y1', borderColor: RT_COLORS.rps,
                  fill: false, pointBackgroundColor: RT_COLORS.rps },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            animation: false,
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, padding: 14, color: tick } },
                tooltip: {
                    callbacks: {
                        label: (it) => {
                            const v = it.parsed.y;
                            const unit = it.datasetIndex === 2 ? ' req/min' : ' %';
                            const name = ['CPU', 'RAM', 'Req/min'][it.datasetIndex];
                            return `${name}: ${it.datasetIndex === 2 ? v : v.toFixed(1)}${unit}`;
                        }
                    }
                }
            },
            scales: {
                x: { ticks: { color: tick, maxTicksLimit: 6, maxRotation: 0 }, grid: { display: false } },
                y: { position: 'left', title: { display: true, text: 'CPU %', color: tick },
                     ticks: { color: tick, maxTicksLimit: 5, precision: 0, callback: v => Math.round(v) + '%' }, grid: { color: grid } },
                y2: { position: 'left', display: false },   // RAM con su propio zoom
                y1: { position: 'right', beginAtZero: true, min: 0, suggestedMax: 10,
                      title: { display: true, text: 'req/min', color: tick },
                      ticks: { color: tick, precision: 0 }, grid: { display: false } },
            }
        }
    });
    _rtApply();
    _rtStartFallback();
}

function updateRealtimeChart(stats) {
    if (!_realtimeChart) { initRealtimeLine(stats); _rtStartFallback(); return; }
    // El stream puede emitir cada segundo; se guarda máx. una muestra cada 1.5 s.
    if (Date.now() - _rtLastPush < 1500) return;
    _rtPushSample(stats || {});
    _rtApply();
    _rtStartFallback();
}

// Si el stream SSE no entrega datos (proxy, pestaña en segundo plano, etc.),
// el gráfico sigue vivo consultando /api/admin/stats cada 3 s.
function _rtStartFallback() {
    if (_rtFallbackTimer) return;
    _rtFallbackTimer = setInterval(async () => {
        if (document.hidden || !_realtimeChart) return;
        if (Date.now() - _rtLastPush < 3500) return;
        try {
            const res = await fetch('/api/admin/stats', { credentials: 'include' });
            const data = await res.json();
            if (data && data.success && data.stats) {
                _rtPushSample(data.stats);
                _rtApply();
            }
        } catch (e) { /* se reintenta en el siguiente ciclo */ }
    }, 3000);
}

function updateCharts(stats) {
    if (_userChart) {
        const activos = stats.usuarios_activos || 0;
        const suspendidos = stats.cuentas_suspendidas || 0;
        const total = stats.total_usuarios || 0;
        const otros = Math.max(0, total - activos - suspendidos);
        _userChart.data.datasets[0].data = [activos, suspendidos, otros];
        _userChart.update('none');
    }
    if (_activityChart) {
        _activityChart.data.datasets[0].data = [
            stats.visitas_hoy || 0,
            stats.logs_hoy || 0,
            stats.notificaciones || 0,
            stats.requests_minuto || 0,
            stats.citas_pendientes || 0,
        ];
        _activityChart.update('none');
    }
    updateRealtimeChart(stats);
}