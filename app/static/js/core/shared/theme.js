let themeTransitionTimer;

function applyThemeState(isDark) {
    const root = document.documentElement;
    if (isDark) {
        root.classList.add('dark-mode');
    } else {
        root.classList.remove('dark-mode');
    }
}

function syncThemeToggleUI(isDark) {
    const themeToggle = document.getElementById('theme-toggle');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');

    if (themeToggle) {
        themeToggle.setAttribute('aria-pressed', String(isDark));
        themeToggle.setAttribute('aria-label', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
        themeToggle.dataset.theme = isDark ? 'dark' : 'light';
    }

    if (sunIcon) sunIcon.classList.toggle('active', !isDark);
    if (moonIcon) moonIcon.classList.toggle('active', isDark);
}

function saveThemeToStorage(theme) {
    try {
        localStorage.setItem('theme', theme);
    } catch (e) {
        console.warn('No se pudo guardar tema:', e);
    }
    
    try {
        document.cookie = 'theme=' + theme + '; path=/; max-age=' + (365*24*60*60) + '; samesite=Lax';
    } catch (e) {
        console.warn('No se pudo guardar cookie:', e);
    }
    
    fetch('/api/theme', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({theme: theme})
    }).catch(() => {});
}

function toggleTheme() {
    const root = document.documentElement;
    root.classList.add('theme-animating');
    window.clearTimeout(themeTransitionTimer);
    void root.offsetWidth;

    const isDark = root.classList.contains('dark-mode');
    const newTheme = isDark ? 'light' : 'dark';
    applyThemeState(newTheme === 'dark');
    saveThemeToStorage(newTheme);
    syncThemeToggleUI(newTheme === 'dark');

    themeTransitionTimer = window.setTimeout(() => {
        root.classList.remove('theme-animating');
    }, 250);
    
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
    return 'light';
}

function initTheme() {
    const isDark = getSavedTheme() === 'dark';
    applyThemeState(isDark);
    syncThemeToggleUI(isDark);
    
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleTheme);
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
        applyThemeState(isDark);
        syncThemeToggleUI(isDark);
    }
});