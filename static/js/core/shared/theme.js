let themeTransitionTimer;
let themeToggleTimer;

const SVG_SUN = `
  <svg class="theme-svg theme-svg-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="5"/>
    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
  </svg>
`;

const SVG_MOON = `
  <svg class="theme-svg theme-svg-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79"/>
  </svg>
`;

function applyThemeState(isDark) {
    const root = document.documentElement;
    if (isDark) {
        root.classList.add('dark-mode');
    } else {
        root.classList.remove('dark-mode');
    }
}

function injectSvgs(themeToggle) {
    if (!themeToggle) return;
    if (themeToggle.querySelector('.theme-svg')) return;

    themeToggle.innerHTML = SVG_SUN + SVG_MOON;
}

function syncThemeToggleUI(isDark) {
    const themeToggle = document.getElementById('theme-toggle');
    const svgSun = themeToggle ? themeToggle.querySelector('.theme-svg-sun') : null;
    const svgMoon = themeToggle ? themeToggle.querySelector('.theme-svg-moon') : null;

    if (themeToggle) {
        themeToggle.setAttribute('aria-pressed', String(isDark));
        themeToggle.setAttribute('aria-label', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
        themeToggle.dataset.theme = isDark ? 'dark' : 'light';
    }

    if (svgSun && svgMoon) {
        if (isDark) {
            svgSun.style.opacity = '0';
            svgSun.style.transform = 'scale(0)';
            svgMoon.style.opacity = '1';
            svgMoon.style.transform = 'scale(1)';
        } else {
            svgSun.style.opacity = '1';
            svgSun.style.transform = 'scale(1)';
            svgMoon.style.opacity = '0';
            svgMoon.style.transform = 'scale(0)';
        }
    }
}

function saveThemeToStorage(theme) {
    try {
        localStorage.setItem('theme', theme);
    } catch (e) {
        console.warn('No se pudo guardar tema:', e);
    }

    try {
        document.cookie = 'theme=' + theme + '; path=/; max-age=' + (365 * 24 * 60 * 60) + '; samesite=Lax';
    } catch (e) {
        console.warn('No se pudo guardar cookie:', e);
    }

    fetch('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: theme })
    }).catch(() => {});
}

function toggleTheme() {
    const root = document.documentElement;
    const themeToggle = document.getElementById('theme-toggle');

    // Agregar clase de animación
    themeToggle.classList.add('toggle-animating');
    root.classList.add('theme-animating');

    window.clearTimeout(themeTransitionTimer);
    window.clearTimeout(themeToggleTimer);

    // Forzar reflow para activar la animación
    void themeToggle.offsetWidth;

    const isDark = root.classList.contains('dark-mode');
    const newTheme = isDark ? 'light' : 'dark';

    applyThemeState(newTheme === 'dark');
    saveThemeToStorage(newTheme);
    syncThemeToggleUI(newTheme === 'dark');

    themeTransitionTimer = window.setTimeout(() => {
        root.classList.remove('theme-animating');
    }, 300);

    themeToggleTimer = window.setTimeout(() => {
        themeToggle.classList.remove('toggle-animating');
    }, 300);

    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: newTheme === 'dark' } }));
}

function getSavedTheme() {
    try {
        const cookieTheme = document.cookie
            .split('; ')
            .find(r => r.startsWith('theme='))
            ?.split('=')[1];
        if (cookieTheme === 'dark') return 'dark';
        if (cookieTheme === 'light') return 'light';

        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') return 'dark';
        if (savedTheme === 'light') return 'light';
    } catch (e) {}
    return 'dark';
}

function initTheme() {
    const isDark = getSavedTheme() === 'dark';
    const themeToggle = document.getElementById('theme-toggle');

    applyThemeState(isDark);

    // Inyectar SVGs si el botón existe
    if (themeToggle) {
        injectSvgs(themeToggle);
        syncThemeToggleUI(isDark);

        themeToggle.addEventListener('click', toggleTheme);
    }
}

(function applyThemeEarly() {
    try {
        const isDark = getSavedTheme() === 'dark';
        const root = document.documentElement;
        if (isDark) {
            root.classList.add('dark-mode');
        } else {
            root.classList.remove('dark-mode');
        }
    } catch (e) {}
})();

if (!document.readyState || document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
} else {
    initTheme();
}

window.addEventListener('storage', function (e) {
    if (e.key === 'theme') {
        const isDark = e.newValue === 'dark';
        const themeToggle = document.getElementById('theme-toggle');
        applyThemeState(isDark);

        if (themeToggle && !themeToggle.querySelector('.theme-svg')) {
            injectSvgs(themeToggle);
        }
        syncThemeToggleUI(isDark);
    }
});