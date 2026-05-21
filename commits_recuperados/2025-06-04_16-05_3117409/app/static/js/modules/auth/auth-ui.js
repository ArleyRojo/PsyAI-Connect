function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn ? btn.querySelector('i') : null;
    if (!input) return;

    if (input.type === 'password') {
        input.type = 'text';
        if (icon) icon.classList.replace('fa-eye', 'fa-eye-slash');
        if (btn) btn.setAttribute('aria-label', 'Ocultar contrasena');
    } else {
        input.type = 'password';
        if (icon) icon.classList.replace('fa-eye-slash', 'fa-eye');
        if (btn) btn.setAttribute('aria-label', 'Mostrar contrasena');
    }
}

(function () {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let W = 0;
    let H = 0;
    const lightPalette = [[144, 202, 249], [100, 181, 246], [179, 229, 252], [33, 150, 243], [207, 226, 255], [66, 165, 245], [21, 101, 192]];
    const darkPalette = [[74, 134, 240], [30, 80, 160], [15, 52, 120], [100, 160, 255], [50, 110, 210], [20, 70, 180], [10, 40, 100]];

    function isDark() {
        return document.documentElement.classList.contains('dark-mode');
    }

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    function buildParticle(startY) {
        const palette = isDark() ? darkPalette : lightPalette;
        const color = palette[Math.floor(Math.random() * palette.length)];
        const opacity = isDark() ? (0.22 + Math.random() * 0.32) : (0.30 + Math.random() * 0.38);
        const radius = 5 + Math.random() * 18;

        return {
            x: 10 + Math.random() * Math.max(W - 20, 100),
            y: startY !== undefined ? startY : H + radius,
            r: radius,
            vx: (Math.random() - 0.5) * 0.5,
            vy: -(0.35 + Math.random() * 0.65),
            color: 'rgba(' + color[0] + ',' + color[1] + ',' + color[2] + ',' + opacity.toFixed(2) + ')'
        };
    }

    let particles = [];

    function init() {
        resize();
        particles = [];
        for (let i = 0; i < 45; i++) {
            particles.push(buildParticle(Math.random() * H));
        }
    }

    function recolor() {
        const palette = isDark() ? darkPalette : lightPalette;
        particles.forEach(function (particle) {
            const color = palette[Math.floor(Math.random() * palette.length)];
            const opacity = isDark() ? (0.22 + Math.random() * 0.32) : (0.30 + Math.random() * 0.38);
            particle.color = 'rgba(' + color[0] + ',' + color[1] + ',' + color[2] + ',' + opacity.toFixed(2) + ')';
        });
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);
        particles.forEach(function (particle) {
            particle.x += particle.vx;
            particle.y += particle.vy;

            if (particle.y + particle.r < 0) {
                Object.assign(particle, buildParticle(H + particle.r));
                particle.x = 10 + Math.random() * (W - 20);
            }
            if (particle.x - particle.r < 0) {
                particle.x = particle.r;
                particle.vx *= -1;
            }
            if (particle.x + particle.r > W) {
                particle.x = W - particle.r;
                particle.vx *= -1;
            }

            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.r, 0, Math.PI * 2);
            ctx.fillStyle = particle.color;
            ctx.fill();
        });

        requestAnimationFrame(draw);
    }

    new MutationObserver(recolor).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class']
    });

    window.addEventListener('resize', resize);
    init();
    draw();
})();
