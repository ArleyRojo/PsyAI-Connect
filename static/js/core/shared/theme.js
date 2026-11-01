let themeTransitionTimer;
let themeToggleTimer;

const EMOJI_SUN = '<span class="theme-emoji theme-emoji-sun" aria-hidden="true">🌞</span>';
const EMOJI_MOON = '<span class="theme-emoji theme-emoji-moon" aria-hidden="true">🌙</span>';

function applyThemeState(isDark) {
    const root = document.documentElement;
    if (isDark) {
        root.classList.add('dark-mode');
    } else {
        root.classList.remove('dark-mode');
    }
}

function injectEmojis(themeToggle) {
    if (!themeToggle) return;
    if (themeToggle.querySelector('.theme-emoji')) return;

    themeToggle.innerHTML = EMOJI_SUN + EMOJI_MOON;
}

function syncThemeToggleUI(isDark) {
    const themeToggle = document.getElementById('theme-toggle');
    const emojiSun = themeToggle ? themeToggle.querySelector('.theme-emoji-sun') : null;
    const emojiMoon = themeToggle ? themeToggle.querySelector('.theme-emoji-moon') : null;

    if (themeToggle) {
        themeToggle.setAttribute('aria-pressed', String(isDark));
        themeToggle.setAttribute('aria-label', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
        themeToggle.dataset.theme = isDark ? 'dark' : 'light';
    }

    if (emojiSun && emojiMoon) {
        if (isDark) {
            emojiSun.style.opacity = '0';
            emojiSun.style.transform = 'scale(0)';
            emojiMoon.style.opacity = '1';
            emojiMoon.style.transform = 'scale(1)';
        } else {
            emojiSun.style.opacity = '1';
            emojiSun.style.transform = 'scale(1)';
            emojiMoon.style.opacity = '0';
            emojiMoon.style.transform = 'scale(0)';
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
    }, 400);

    themeToggleTimer = window.setTimeout(() => {
        themeToggle.classList.remove('toggle-animating');
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
    const themeToggle = document.getElementById('theme-toggle');

    applyThemeState(isDark);

    // Inyectar emojis si el botón existe
    if (themeToggle) {
        injectEmojis(themeToggle);
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

        if (themeToggle && !themeToggle.querySelector('.theme-emoji')) {
            injectEmojis(themeToggle);
        }
        syncThemeToggleUI(isDark);
    }
});