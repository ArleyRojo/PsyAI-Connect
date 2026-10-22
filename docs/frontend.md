# Frontend — PsyAI Connect

> **Resumen:** Organización del frontend (HTML/CSS/JS vanilla), carga de scripts, sistema de notificaciones, tema claro/oscuro y convenciones de nombres.  
> **Audiencia:** Desarrolladores frontend y full-stack que tocan la UI.

---

## 1. Estructura de `static/`

```
static/
├── css/
│   ├── base/
│   │   └── base.css          # Variables CSS globales, reset, utilidades
│   ├── components/
│   │   ├── components.css    # Componentes UI reutilizables (botones, cards, forms, toasts)
│   │   ├── custom-alerts.css # Estilos para PsyAIAlerts
│   │   ├── card-3d.css       # Tarjetas 3D (landing)
│   │   └── cookies.css       # Banner de cookies
│   ├── layout/
│   │   └── layout.css        # Layout general (sidebar, header, grid)
│   ├── pages/
│   │   ├── landing.css       # Landing page pública
│   │   ├── patient.css       # Portal paciente
│   │   ├── professional.css  # Portal profesional
│   │   ├── admin.css         # Panel admin
│   │   └── auth.css          # Login, registro, recuperación
│   ├── themes/
│   │   └── theme.css         # Modo oscuro (html.dark-mode) + tokens
│   └── responsive/
│       ├── index.css         # Media queries globales
│       ├── responsive-fix.css# Fixes específicos
│       └── *.css             # Por app/página
├── js/
│   ├── base/                 # Scripts de páginas públicas (landing)
│   │   ├── hero-carousel.js
│   │   ├── index.js
│   │   ├── landing.js
│   │   └── navbar-scroll.js
│   ├── core/
│   │   └── shared/           # Utilidades globales (cargadas en TODAS las páginas autenticadas)
│   │       ├── account-status.js   # Manejo global de cuenta suspendida (aviso y redirección)
│   │       ├── alerts.js           # PsyAIAlerts (toasts)
│   │       ├── aside.js            # Sidebar colapsable
│   │       ├── connection-status.js# Offline/servidor caído/chatbot
│   │       ├── csrf.js             # Helper CSRF (fetchWithCsrf)
│   │       ├── localStorage-detector.js
│   │       ├── mobile-navbar-toggle.js
│   │       ├── nombre.usuario.js   # Nombre en header
│   │       ├── scroll-reveal.js    # Animaciones on scroll
│   │       ├── theme-inline.js     # Inline para evitar flash
│   │       └── theme.js            # Toggle tema claro/oscuro
│   ├── modules/
│   │   ├── auth/               # Login, registro, recuperación
│   │   ├── patient/            # Módulos del portal paciente
│   │   │   ├── chatbot.js
│   │   │   ├── agendaquotes.js
│   │   │   ├── evolution.js
│   │   │   ├── historia_clinica_paciente.js
│   │   │   ├── my.profile.js
│   │   │   └── aside.js
│   │   ├── professional/       # Módulos del portal profesional
│   │   │   ├── anamnesis.js            # Anamnesis y antecedentes familiares (historia clínica)
│   │   │   ├── my.agenda.js
│   │   │   ├── patients.js
│   │   │   ├── patients.evolution.js
│   │   │   ├── patients.prediagnostico.js # Prediagnósticos del chatbot por paciente
│   │   │   ├── historia_clinica_pro.js
│   │   │   ├── my.profile2.js
│   │   │   ├── reports.js
│   │   │   └── aside.js
│   │   ├── admin/              # Módulos del panel admin
│   │   │   ├── admin.dashboard.js
│   │   │   ├── admin.dashboard.charts.js  # Gráficas (Chart.js)
│   │   │   ├── admin.dashboard.sse.js     # Métricas en vivo por SSE
│   │   │   ├── admin.dashboard.utils.js   # escapeHtml, csvCell y utilidades compartidas
│   │   │   ├── admin.users.js
│   │   │   ├── admin.roles.js
│   │   │   ├── admin.logs.js
│   │   │   ├── admin.notifications.js
│   │   │   ├── admin.rendimiento.js
│   │   │   └── admin.chatbot.config.js
│   │   └── shared/             # Compartidos entre roles
│   │       └── direct-chat.js  # Chat SSE paciente–profesional
│   └── vendor/
│       └── chart.umd.min.js    # Chart.js para gráficos admin
├── img/                        # Assets estáticos (logos, avatares, etc.)
└── responsive/                 # CSS responsive adicional
```

---

## 2. Carga de scripts en templates

### Páginas públicas (landing)
`templates/base/index.html` carga en `<head>`:
```html
<link rel="stylesheet" href="/css/base/base.css">
<link rel="stylesheet" href="/css/layout/layout.css">
<link rel="stylesheet" href="/css/themes/theme.css">
<link rel="stylesheet" href="/css/components/components.css">
<link rel="stylesheet" href="/css/pages/landing.css">
<script src="/js/core/shared/theme-inline.js"></script>  <!-- Evita flash de tema -->
<script src="/js/core/shared/theme.js"></script>
```

Al final de `<body>`:
```html
<script src="/js/base/landing.js"></script>
<script src="/js/base/navbar-scroll.js"></script>
```

### Páginas autenticadas (dashboards)
Cada template de dashboard incluye `templates/base/partials/scripts.html` al final:
```html
{% include 'base/partials/scripts.html' %}
```

**`templates/base/partials/scripts.html`** carga:
```html
<script src="/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
<script src="/js/core/shared/connection-status.js"></script>
<!-- Error reporter global -->
<script> ... window.addEventListener("error", ...) ... </script>
```

Luego cada página añade sus módulos específicos:
```html
<!-- chatbot.html -->
<script src="/js/core/shared/alerts.js"></script>
<script src="/js/modules/patient/aside.js"></script>
<script src="/js/modules/patient/chatbot.js"></script>
```

> **Regla:** Los scripts de `core/shared/` se cargan **una sola vez** vía `scripts.html`. Los módulos específicos de cada página se cargan en su template correspondiente.

---

## 3. Sistema de notificaciones — `PsyAIAlerts`

**Archivo:** `static/js/core/shared/alerts.js`  
**Objeto global:** `window.PsyAIAlerts` (también `window.mostrarToast` para API simple).

### API

```js
// API completa
PsyAIAlerts.show({
  type: 'success' | 'error' | 'warning' | 'info' | 'welcome' | 'reminder',
  title: 'Título opcional',
  message: 'Mensaje principal',
  duration: 4000,        // ms, 0 = no auto-cerrar
  icon: 'fa-custom-icon' // opcional, override por tipo
});

// Shortcuts
PsyAIAlerts.success(message, title)
PsyAIAlerts.error(message, title)
PsyAIAlerts.warning(message, title)
PsyAIAlerts.info(message, title)
PsyAIAlerts.welcome(name, role)  // role: 'paciente'|'profesional'|'admin'
PsyAIAlerts.reminder(title, message)

// Legacy simple
mostrarToast(mensaje, tipo, duracion)
```

### Comportamiento
- Contenedor fijo `top:20px right:20px` z-index 99999
- Máximo 3 toasts simultáneos (el más viejo se elimina)
- Animación de entrada/salida con barra de progreso
- Pause al hover, reanudar al salir
- Dark mode automático (lee `document.documentElement.classList.contains('dark-mode')`)

### Estilos
CSS en `static/css/components/custom-alerts.css` (contenedor, animaciones, tipos).

---

## 4. Tema claro/oscuro

### Variables CSS (`static/css/themes/theme.css`)
Tokens semánticos definidos en `:root` (claro) y sobrescritos en `html.dark-mode`:

| Token | Claro | Oscuro |
|-------|-------|--------|
| `--surface-canvas` | `#fff` | `#0A1220` |
| `--surface-card` | `#fff` | `#101B2E` |
| `--surface-card-hover` | `#f8faff` | `#142238` |
| `--text-primary` | `#0D1F3C` | `#EAF1FB` |
| `--text-secondary` | `#4A5568` | `#A9BAD4` |
| `--text-muted` | `#7B92AC` | `#6F84A6` |
| `--brand-500` | `#2F6FE4` | `#4A8AF4` |
| `--border-subtle` | `#D6E8FA` | `#1C2D48` |
| `--elev-1/2/3` | sombras claras | sombras oscuras |

### Toggle (`static/js/core/shared/theme.js`)
```js
// Al cargar: lee cookie 'theme' o localStorage
// Toggle: alterna clase 'dark-mode' en <html>
// Persiste: cookie 'theme' (1 año) + localStorage
// Dispara evento personalizado 'themechanged'
```

### HTML
```html
<!-- En <head> inline para evitar flash -->
<script src="/js/core/shared/theme-inline.js"></script>

<!-- Botón en sidebar/header -->
<div class="theme-switch-container">
  <i class="fa-solid fa-sun theme-icon sun" id="sun-icon"></i>
  <button id="theme-toggle" title="Cambiar modo"></button>
  <i class="fa-solid fa-moon theme-icon moon" id="moon-icon"></i>
</div>
```

---

## 5. Helper CSRF — `static/js/core/shared/csrf.js`

Wrapper `fetch` que inyecta `X-CSRFToken` automáticamente en `POST/PUT/PATCH/DELETE`.

```js
import { fetchWithCsrf, initCsrfToken } from '/js/core/shared/csrf.js';

// Uso directo
const resp = await fetchWithCsrf('/api/facturas', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
});

// O vía global
window.PsyAICsrf.fetch(url, options)
```

**Fuentes del token (en orden):**
1. Cookie `csrftoken` (si `CSRF_COOKIE_HTTPONLY=False` en dev)
2. Meta tag `<meta name="csrf-token" content="{{ csrf_token }}">` (inyectado en `head.html`)
3. Variable global `window.CSRF_TOKEN` (inyectada por `initCsrfToken()` al cargar)

**Auto-inicialización:** `initCsrfToken()` se ejecuta al `DOMContentLoaded` y hace `GET /api/csrf/` para poblar `window.CSRF_TOKEN`.

---

## 6. Manejo de conexión — `connection-status.js`

**Archivo:** `static/js/core/shared/connection-status.js`  
**Global:** `window.PsyAIConnection`

### Funcionalidades
- **Offline/Online:** Listeners `window.online/offline` → tarjeta no bloqueante "Sin conexión" / "Conexión restablecida" (toast).
- **Servidor caído:** `fetchWithConnectionHandling()` / `fetchConTimeout()` (5s default) → tarjeta "Estamos teniendo dificultades" con botón Reintentar.
- **Error chatbot:** `showChatbotError(mensaje, retryCallback)` → burbuja de error dentro del chat con botón Reintentar que re-ejecuta `enviarMensaje(mensaje)`.

### API
```js
PsyAIConnection.showConnectionError({ title, message, icon, onRetry })
PsyAIConnection.fetchConTimeout(url, options, timeoutMs)
PsyAIConnection.fetchWithConnectionHandling(url, options, { onRetry })
PsyAIConnection.showChatbotError(mensaje, retryCallback)
PsyAIConnection.isOnline()
```

### UI
Estilos en `static/css/components/components.css`:
- `.psyai-connection-card` — overlay fijo bottom-center
- `.error-bubble` — burbuja dentro de `#chat-area`

---

## 7. Convenciones de código

### JavaScript
- **Vanilla ES6+** (sin transpiler, sin framework)
- Módulos por archivo, sin bundler; carga via `<script src="...">`
- Nomenclatura: `camelCase` para variables/funciones, `PascalCase` para clases/constructores
- `const`/`let`, `async/await` para promesas
- Manejo de errores con `try/catch` + `console.error`
- Comentarios JSDoc en funciones públicas

### CSS
- **Variables CSS** obligatorias (tokens de `theme.css`), nada de valores hardcoded
- Metodología BEM-ish: `.componente__elemento--modificador`
- Media queries mobile-first en `responsive/index.css` y `responsive-fix.css`
- Dark mode via `html.dark-mode` selector (no media query `prefers-color-scheme`)

### HTML / Templates
- Django templates con herencia (`base.html` → parciales)
- Partials reutilizables en `templates/base/partials/`
- `{% csrf_token %}` en formularios POST tradicionales
- Meta tag CSRF: `<meta name="csrf-token" content="{{ csrf_token }}">`

---

## 8. Archivos JS principales por página

| Página | Scripts principales (orden de carga) |
|--------|--------------------------------------|
| Landing | `theme-inline.js` → `theme.js` → `landing.js` → `navbar-scroll.js` |
| Login/Registro | `scripts.html` → `auth-guard.js` → `login.js` / `register.js` → `logout.js` |
| Paciente Dashboard | `scripts.html` → `alerts.js` → `aside.js` → `chatbot.js` / `agendaquotes.js` / `evolution.js` / `historia_clinica_paciente.js` / `my.profile.js` |
| Profesional Dashboard | `scripts.html` → `alerts.js` → `aside.js` → `my.agenda.js` / `patients.js` / `reports.js` / `historia_clinica_pro.js` / `my.profile2.js` |
| Admin Dashboard | `scripts.html` → `alerts.js` → `admin.dashboard.js` / `admin.users.js` / `admin.roles.js` / `admin.logs.js` / `admin.notifications.js` / `admin.rendimiento.js` / `admin.chatbot.config.js` |
| Chat directo | `scripts.html` → `alerts.js` → `direct-chat.js` (compartido) |

---

## Ver también

- [`modelos-de-datos.md`](modelos-de-datos.md) — Modelos que consumen estos scripts
- [`chatbot-ia.md`](chatbot-ia.md) — Detalle de `chatbot.js`
- [`pagos-facturacion.md`](pagos-facturacion.md) — `agendaquotes.js` y pago Wompi
- [`seguridad.md`](seguridad.md) — CSRF, conexión, CSP
- [`despliegue.md`](despliegue.md) — Build de assets estáticos en Docker