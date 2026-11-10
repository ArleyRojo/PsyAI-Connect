// Gráfica "Tiempo real" del dashboard admin (CPU, RAM y peticiones por minuto).
// Las demás piezas del dashboard (tarjetas, barras por hora, medidores) se pintan
// sin librería en admin.dashboard.js.
let _realtimeChart = null;
const REALTIME_POINTS = 30;

function initCharts(stats) {
    initRealtimeLine(stats);
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
    updateRealtimeChart(stats);
}
