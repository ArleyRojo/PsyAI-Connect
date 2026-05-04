(function () {
    const MOBILE_QUERY = '(max-width: 991.98px)';
    const INITIAL_SYNC_DELAYS = [0, 120, 320, 800];
    let scheduled = false;
    let observerStarted = false;

    function isMobileViewport() {
        return window.matchMedia(MOBILE_QUERY).matches;
    }

    function createLine() {
        const line = document.createElement('span');
        line.className = 'custom-toggler-line';
        return line;
    }

    function createToggler() {
        const toggler = document.createElement('button');
        toggler.className = 'navbar-toggler border-0';
        toggler.type = 'button';
        toggler.setAttribute('data-bs-toggle', 'collapse');
        toggler.setAttribute('data-bs-target', '#navmenu');
        toggler.setAttribute('aria-controls', 'navmenu');
        toggler.setAttribute('aria-expanded', 'false');
        toggler.setAttribute('aria-label', 'Abrir navegacion');
        return toggler;
    }

    function ensureMarkup(toggler) {
        if (!toggler) return null;

        toggler.classList.add('navbar-toggler', 'border-0');
        toggler.type = 'button';
        toggler.setAttribute('data-bs-toggle', 'collapse');
        toggler.setAttribute('data-bs-target', '#navmenu');
        toggler.setAttribute('aria-controls', 'navmenu');

        if (!toggler.getAttribute('aria-label')) {
            toggler.setAttribute('aria-label', 'Abrir navegacion');
        }

        let icon = toggler.querySelector('.custom-toggler-icon');
        if (!icon) {
            icon = document.createElement('span');
            icon.className = 'custom-toggler-icon';
            icon.setAttribute('aria-hidden', 'true');
            toggler.prepend(icon);
        } else {
            icon.setAttribute('aria-hidden', 'true');
        }

        if (icon.querySelectorAll('.custom-toggler-line').length !== 3) {
            icon.replaceChildren(createLine(), createLine(), createLine());
        }

        let label = toggler.querySelector('.navbar-toggler-label');
        if (!label) {
            label = document.createElement('span');
            label.className = 'navbar-toggler-label';
            toggler.appendChild(label);
        }

        if (!label.textContent.trim()) {
            label.textContent = '';
        }

        if (toggler.firstElementChild !== icon) {
            toggler.prepend(icon);
        }

        if (toggler.lastElementChild !== label) {
            toggler.appendChild(label);
        }

        if (!toggler.hasAttribute('aria-expanded')) {
            toggler.setAttribute('aria-expanded', 'false');
        }

        return toggler;
    }

    function getNavbarParts() {
        const nav = document.getElementById('mainNav');
        if (!nav) return {};

        const container = nav.querySelector('.container');
        const navmenu = nav.querySelector('#navmenu');
        if (!container || !navmenu) return { nav, container, navmenu };

        let toggler = container.querySelector('.navbar-toggler');
        if (!toggler) {
            toggler = createToggler();
            container.insertBefore(toggler, navmenu);
        }

        ensureMarkup(toggler);

        if (toggler.nextElementSibling !== navmenu) {
            container.insertBefore(toggler, navmenu);
        }

        return { nav, container, navmenu, toggler };
    }

    function syncNavbarBrandTrigger(brand, isMobile) {
        if (!brand) return;

        if (!brand.dataset.mobileNavbarManaged) {
            brand.dataset.mobileNavbarManaged = 'true';
            brand.dataset.desktopToggle = brand.getAttribute('data-bs-toggle') || '';
            brand.dataset.desktopTarget = brand.getAttribute('data-bs-target') || '';
            brand.dataset.desktopHref = brand.getAttribute('href') || '#';

            brand.addEventListener('click', function (event) {
                if (isMobileViewport()) {
                    event.preventDefault();
                }
            });
        }

        if (isMobile) {
            brand.removeAttribute('data-bs-toggle');
            brand.removeAttribute('data-bs-target');
            brand.setAttribute('href', '#');
            brand.setAttribute('aria-disabled', 'true');
        } else {
            if (brand.dataset.desktopToggle) {
                brand.setAttribute('data-bs-toggle', brand.dataset.desktopToggle);
            }

            if (brand.dataset.desktopTarget) {
                brand.setAttribute('data-bs-target', brand.dataset.desktopTarget);
            }

            brand.setAttribute('href', brand.dataset.desktopHref || '#');
            brand.removeAttribute('aria-disabled');
        }
    }

    function resetDesktopCollapse(navmenu, toggler) {
        if (!navmenu || !toggler) return;

        navmenu.classList.remove('show', 'collapsing');
        navmenu.style.removeProperty('height');
        navmenu.style.removeProperty('overflow');
        navmenu.style.removeProperty('display');
        toggler.setAttribute('aria-expanded', 'false');

        if (window.bootstrap && window.bootstrap.Collapse) {
            const instance = window.bootstrap.Collapse.getInstance(navmenu);
            if (instance) {
                instance._isTransitioning = false;
            }
        }
    }

    function syncExpandedState(navmenu, toggler) {
        if (!navmenu || !toggler) return;
        toggler.setAttribute('aria-expanded', navmenu.classList.contains('show') ? 'true' : 'false');
    }

    function syncNavbar() {
        scheduled = false;

        const { nav, navmenu, toggler } = getNavbarParts();
        if (!nav || !navmenu || !toggler) return;

        const isMobile = isMobileViewport();
        syncNavbarBrandTrigger(nav.querySelector('.navbar-brand'), isMobile);

        if (!isMobile) {
            resetDesktopCollapse(navmenu, toggler);
        }

        syncExpandedState(navmenu, toggler);
    }

    function scheduleSync() {
        if (scheduled) return;
        scheduled = true;
        window.requestAnimationFrame(syncNavbar);
    }

    function startObserver() {
        if (observerStarted) return;
        observerStarted = true;

        const { nav, navmenu } = getNavbarParts();
        if (!nav || !navmenu) return;

        const observer = new MutationObserver(scheduleSync);
        observer.observe(nav, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['class', 'style', 'aria-expanded', 'data-bs-toggle', 'data-bs-target']
        });

        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['class']
        });
    }

    function bootstrapSync() {
        startObserver();
        scheduleSync();

        INITIAL_SYNC_DELAYS.forEach((delay) => {
            window.setTimeout(scheduleSync, delay);
        });

        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(scheduleSync).catch(function () {});
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootstrapSync);
    } else {
        bootstrapSync();
    }

    window.addEventListener('load', scheduleSync);
    window.addEventListener('resize', scheduleSync);
    window.addEventListener('orientationchange', scheduleSync);
    window.addEventListener('pageshow', scheduleSync);
    window.addEventListener('themeChanged', scheduleSync);

    document.addEventListener('shown.bs.collapse', scheduleSync);
    document.addEventListener('hidden.bs.collapse', scheduleSync);

    const mediaQuery = window.matchMedia ? window.matchMedia(MOBILE_QUERY) : null;
    if (mediaQuery) {
        if (typeof mediaQuery.addEventListener === 'function') {
            mediaQuery.addEventListener('change', scheduleSync);
        } else if (typeof mediaQuery.addListener === 'function') {
            mediaQuery.addListener(scheduleSync);
        }
    }
})();
