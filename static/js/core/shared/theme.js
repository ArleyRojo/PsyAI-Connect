let themeTransitionTimer;
let themeToggleTimer;

const TOGGLE_SELECTOR = '#theme-toggle, .theme-toggle-mobile';

function getToggles() {
    return document.querySelectorAll(TOGGLE_SELECTOR);
}

function applyThemeState(isDark) {
    const root = document.documentElement;
    if (isDark) {
        root.classList.add('dark-mode');
    } else {
        root.classList.remove('dark-mode');
    }
}

function updateToggleUI(themeToggle, isDark) {
    if (!themeToggle) return;

    // Un solo span con el emoji correspondiente
    themeToggle.innerHTML = isDark
        ? '<span class="theme-emoji" aria-hidden="true">🌙</span>'
        : '<span class="theme-emoji" aria-hidden="true">☀️</span>';

    themeToggle.setAttribute('aria-pressed', String(isDark));
    themeToggle.setAttribute('aria-label', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    themeToggle.setAttribute('title', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    themeToggle.dataset.theme = isDark ? 'dark' : 'light';
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

function toggleTheme(event) {
    const currentToggle = event && event.currentTarget ? event.currentTarget : document.querySelector(TOGGLE_SELECTOR);
    const root = document.documentElement;

    if (currentToggle) {
        currentToggle.classList.add('toggle-animating');
    }
    root.classList.add('theme-animating');

    window.clearTimeout(themeTransitionTimer);
    window.clearTimeout(themeToggleTimer);

    void root.offsetWidth;

    const isDark = root.classList.contains('dark-mode');
    const newTheme = isDark ? 'light' : 'dark';

    applyThemeState(newTheme === 'dark');
    saveThemeToStorage(newTheme);
    getToggles().forEach((t) => updateToggleUI(t, newTheme === 'dark'));

    themeTransitionTimer = window.setTimeout(() => {
        root.classList.remove('theme-animating');
    }, 400);

    themeToggleTimer = window.setTimeout(() => {
        getToggles().forEach((t) => t.classList.remove('toggle-animating'));
    }, 400);

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
    applyThemeState(isDark);

    getToggles().forEach((themeToggle) => {
        updateToggleUI(themeToggle, isDark);
        themeToggle.addEventListener('click', toggleTheme);
    });
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
        applyThemeState(isDark);
        getToggles().forEach((themeToggle) => {
            updateToggleUI(themeToggle, isDark);
        });
    }
});