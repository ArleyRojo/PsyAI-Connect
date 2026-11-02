let themeTransitionTimer;
let themeToggleTimer;

const TOGGLE_SELECTOR = '#theme-toggle, .theme-toggle-mobile';

const SUN_HTML = '<span class="theme-emoji theme-emoji-sun" aria-hidden="true">☀️</span>';
const MOON_HTML = '<span class="theme-emoji theme-emoji-moon" aria-hidden="true">🌙</span>';

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

function injectEmojis(themeToggle) {
    if (!themeToggle) return;
    if (themeToggle.querySelector('.theme-emoji')) return;

    themeToggle.innerHTML = SUN_HTML + MOON_HTML;
}

function updateToggleUI(themeToggle, isDark) {
    if (!themeToggle) return;

    const emojiSun = themeToggle.querySelector('.theme-emoji-sun');
    const emojiMoon = themeToggle.querySelector('.theme-emoji-moon');

    themeToggle.setAttribute('aria-pressed', String(isDark));
    themeToggle.setAttribute('aria-label', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    themeToggle.setAttribute('title', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    themeToggle.dataset.theme = isDark ? 'dark' : 'light';

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

function toggleTheme(event) {
    const currentToggle = event && event.currentTarget ? event.currentTarget : document.querySelector(TOGGLE_SELECTOR);
    const root = document.documentElement;

    if (currentToggle) {
        currentToggle.classList.add('toggle-animating');
    }

    const isDark = root.classList.contains('dark-mode');
    const newTheme = isDark ? 'light' : 'dark';

    // En móvil/tablet: cambio instantáneo en la página (sin transición parcial tosca),
    // solo el toggle button anima suavemente.
    const isMobileViewport = window.matchMedia('(max-width: 991px)').matches;

    if (isMobileViewport) {
        // Cambio visual inmediato
        applyThemeState(newTheme === 'dark');
        getToggles().forEach((t) => updateToggleUI(t, newTheme === 'dark'));

        // Diferir guardado y evento al siguiente cuadro
        window.requestAnimationFrame(() => {
            window.queueMicrotask(() => {
                saveThemeToStorage(newTheme);
                window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: newTheme === 'dark' } }));
            });
        });

        themeToggleTimer = window.setTimeout(() => {
            getToggles().forEach((t) => t.classList.remove('toggle-animating'));
        }, 150);
        return;
    }

    // Escritorio: transición suave con theme-animating
    root.classList.add('theme-animating');
    root.classList.add('theme-switching');

    window.requestAnimationFrame(() => {
        applyThemeState(newTheme === 'dark');
        getToggles().forEach((t) => updateToggleUI(t, newTheme === 'dark'));

        window.queueMicrotask(() => {
            saveThemeToStorage(newTheme);
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: newTheme === 'dark' } }));
        });
    });

    themeTransitionTimer = window.setTimeout(() => {
        root.classList.remove('theme-animating');
        root.classList.remove('theme-switching');
    }, 260);

    themeToggleTimer = window.setTimeout(() => {
        getToggles().forEach((t) => t.classList.remove('toggle-animating'));
    }, 260);
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
        injectEmojis(themeToggle);
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
            injectEmojis(themeToggle);
            updateToggleUI(themeToggle, isDark);
        });
    }
});