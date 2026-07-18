let _userChart = null;
let _activityChart = null;
let _realtimeChart = null;
const REALTIME_POINTS = 20;

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

function initRealtimeLine(stats) {
    const ctx = document.getElementById('chartRealtime');
    if (!ctx) return;
    if (_realtimeChart) { _realtimeChart.destroy(); }
    const cpu = stats.cpu || 0;
    const ram = stats.ram || 0;
    const rps = stats.requests_minuto || 0;
    _realtimeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(REALTIME_POINTS).fill(''),
            datasets: [
                {
                    label: 'CPU %',
                    data: Array(REALTIME_POINTS - 1).fill(null).concat([cpu]),
                    borderColor: '#42A5F5',
                    backgroundColor: 'rgba(66, 165, 245, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                },
                {
                    label: 'RAM %',
                    data: Array(REALTIME_POINTS - 1).fill(null).concat([ram]),
                    borderColor: '#66BB6A',
                    backgroundColor: 'rgba(102, 187, 106, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                },
                {
                    label: 'Req/min',
                    data: Array(REALTIME_POINTS - 1).fill(null).concat([rps]),
                    borderColor: '#FFA726',
                    backgroundColor: 'rgba(255, 167, 38, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, padding: 12 } },
            },
            scales: {
                y: { beginAtZero: true, max: 100, title: { display: true, text: '%' } },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    grid: { display: false },
                    title: { display: true, text: 'req/min' },
                }
            }
        }
    });
}

function updateRealtimeChart(stats) {
    if (!_realtimeChart) return;
    const cpu = stats.cpu ?? _realtimeChart.data.datasets[0].data.at(-1) ?? 0;
    const ram = stats.ram ?? _realtimeChart.data.datasets[1].data.at(-1) ?? 0;
    const rps = stats.requests_minuto ?? _realtimeChart.data.datasets[2].data.at(-1) ?? 0;
    _realtimeChart.data.datasets[0].data.push(cpu);
    _realtimeChart.data.datasets[1].data.push(ram);
    _realtimeChart.data.datasets[2].data.push(rps);
    if (_realtimeChart.data.datasets[0].data.length > REALTIME_POINTS) {
        _realtimeChart.data.datasets[0].data.shift();
        _realtimeChart.data.datasets[1].data.shift();
        _realtimeChart.data.datasets[2].data.shift();
    }
    _realtimeChart.update('none');
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
