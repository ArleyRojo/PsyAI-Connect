# Frontend — PsyAI Connect

> **Resumen:** Organización del frontend (HTML, CSS y JavaScript vanilla sobre plantillas Django), carga de estilos y scripts, cliente HTTP con CSRF, notificaciones, tema claro/oscuro y convenciones.
> **Audiencia:** Desarrolladores frontend y full-stack que tocan la UI.

---

## 1. Estructura de `static/`

```
static/
├── css/
│   ├── base/
│   │   ├── base.css            # Variables globales (tokens del tema claro), reset, utilidades
│   │   └── animations.css      # Animaciones (sin referencias en plantillas)
│   ├── components/
│   │   ├── components.css      # Componentes reutilizables (botones, cards, formularios)
│   │   ├── custom-alerts.css   # Estilos de PsyAIAlerts
│   │   ├── custom-select.css   # Select personalizado
│   │   ├── card-3d.css         # Tarjetas 3D (landing)
│   │   └── cookies.css         # Banner de cookies (sin referencias en plantillas)
│   ├── layout/
│   │   └── layout.css          # Layout general (sidebar, header, grid)
│   ├── pages/
│   │   ├── landing.css                    # Landing pública
│   │   ├── auth.css                       # Login, registro, recuperación
│   │   ├── patient.css                    # Portal del paciente
│   │   ├── patient-dashboard-v2.css       # Dashboard del paciente (v2)
│   │   ├── patient-agenda-v2.css          # Agenda del paciente (v2)
│   │   ├── patient-facturas-v2.css        # Facturas del paciente (v2)
│   │   ├── evolution-polish.css           # Evolución
│   │   ├── historia_clinica_paciente.css  # Historia clínica (paciente)
│   │   ├── historia_clinica_pro.css       # Historia clínica (profesional)
│   │   ├── professional.css               # Portal del profesional
│   │   └── admin.css                      # Panel de administración
│   └── themes/
│       ├── theme.css           # Tokens y reglas del modo oscuro (html.dark-mode)
│       └── dark-polish.css     # Ajustes finos del modo oscuro
├── responsive/                 # CSS responsive (fuera de css/)
│   ├── index.css               # Landing
│   ├── responsive-fix.css      # Correcciones globales, se carga al final
│   ├── responsive-admin.css
│   ├── responsive-professional.css
│   ├── auth.css                # (sin referencias en plantillas)
│   └── general.css             # (sin referencias en plantillas)
├── js/
│   ├── base/                   # Landing
│   │   ├── index.js            # Único script de landing cargado por index.html
│   │   ├── landing.js          # (sin referencias)
│   │   ├── hero-carousel.js    # (sin referencias)
│   │   └── navbar-scroll.js    # (sin referencias)
│   ├── components/
│   │   └── custom-select.js
│   ├── core/shared/            # Utilidades globales
│   │   ├── csrf.js                     # CSRF automático sobre fetch
│   │   ├── api-connection.js           # window.PsyAIConnection (cliente HTTP)
│   │   ├── connection-status.js        # Indicador "En línea / Sin conexión"
│   │   ├── account-status.js           # Manejo de cuenta suspendida
│   │   ├── alerts.js                   # window.PsyAIAlerts (toasts)
│   │   ├── theme-inline.js             # Aplica el tema antes de pintar
│   │   ├── theme.js                    # Alternar tema claro/oscuro
│   │   ├── localStorage-detector.js
│   │   ├── mobile-navbar-toggle.js
│   │   ├── nombre.usuario.js           # Nombre en el encabezado
│   │   ├── professional-notifications.js
│   │   ├── aside.js                    # Sidebar del panel admin
│   │   └── scroll-reveal.js            # (sin referencias)
│   ├── modules/
│   │   ├── auth/       # auth-guard, auth-ui, login, logout, register, recover
│   │   ├── patient/    # aside, chatbot, agendaquotes, evolution, historia_clinica_paciente, my.profile
│   │   ├── professional/  # aside, my.agenda, patients, patients.evolution, patients.prediagnostico,
│   │   │                  # anamnesis, historia_clinica_pro, my.profile2, reports
│   │   ├── admin/      # admin.dashboard (+ .utils, .sse, .charts), users, roles, logs,
│   │   │               # notifications, rendimiento, chatbot.config
│   │   └── shared/
│   │       └── direct-chat.js   # Chat paciente–profesional
│   └── vendor/
│       └── chart.umd.min.js     # Chart.js (autoalojado)
├── vendor/                     # Librerías locales: bootstrap, font-awesome, aos, tabler-icons, fonts
└── img/                        # Logos, hero, favicon
```

Las plantillas referencian los assets con rutas absolutas (`/css/...`, `/js/...`, `/vendor/...`, `/responsive/...`) y casi todos llevan un parámetro de versión para invalidar la caché (por ejemplo `?v=20261030-2`).

---

## 2. Carga de estilos y scripts

### Parcial `templates/base/partials/head.html`

Lo incluyen las plantillas dentro de `<head>`. Contiene, en este orden:

1. Metas (`viewport`, `csrf-token` con `{% csrf_token_value %}`) y una función global `getCsrfToken()`.
2. Fuentes locales (`/vendor/fonts/fonts.css`, Plus Jakarta Sans y Lora), Bootstrap 5 y Font Awesome 6, también locales.
3. **SweetAlert2 desde CDN** (`cdn.jsdelivr.net`), con estilos propios para igualarlo a las alertas de PsyAI y una configuración global (`Swal.mixin`) con los botones de Bootstrap.
4. CSS núcleo cargado de forma diferida (`preload` + `media="print" onload`): `base.css`, `layout.css`, `theme.css`, `components.css` y `dark-polish.css`.
5. JS núcleo: `theme-inline.js`, `theme.js`, `localStorage-detector.js`, `csrf.js` y `professional-notifications.js` (`defer`).
6. Reglas de especulación (`speculationrules`) para precargar navegaciones internas, excepto `/api/*` y `/logout*`.
7. Variables globales de cobro: `window.PAGO_CUENTA_URL` y `window.PAGO_CUENTA_NOMBRE`.

### Parcial `templates/base/partials/scripts.html`

Lo incluyen los dashboards al final del `<body>`:

- `bootstrap.bundle.min.js`
- `connection-status.js`, `csrf.js`, `account-status.js`, `api-connection.js` (todos `defer`)
- Un reportero global de errores que envía los errores de JavaScript y las promesas rechazadas a `POST /api/client-errors` (con `sendBeacon`).

### Landing (`templates/base/index.html`)

Incluye `head.html` y añade `aos.css`, `landing.css`, `card-3d.css` y `responsive/index.css`. Al final del `<body>` carga `bootstrap.bundle`, `aos.js`, `responsive-fix.css`, `custom-alerts.css`, `alerts.js`, `mobile-navbar-toggle.js` y `js/base/index.js`. Incluye también un script en línea para el formulario del boletín (`/api/newsletter/subscribe`).

### Páginas autenticadas

Cada plantilla añade sus módulos después de los parciales. Los scripts de `core/shared/` se cargan una sola vez, vía `head.html` y `scripts.html`; los módulos de cada página se cargan en su propia plantilla.

---

## 3. Cliente HTTP y CSRF

La API usa sesiones y CSRF (ver `API_DOCUMENTATION.md`). En el navegador hay tres piezas que trabajan juntas.

### `csrf.js` — CSRF automático

Es un script clásico (no un módulo ES). Expone `window.CSRF` (`getToken()`, `getHeaderName()`) y **reemplaza `window.fetch`**: en cada `POST`, `PUT`, `PATCH` o `DELETE` agrega la cabecera `X-CSRFToken` y fuerza `credentials: 'include'`.

El token se lee de `<meta name="csrf-token">` y, si no está, de la cookie `csrftoken`.

```js
// No hace falta añadir el token a mano
await fetch('/api/citas/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ idProfesional: 7, fecha: '2026-11-10', hora: '09:00' })
});
```

### `api-connection.js` — `window.PsyAIConnection`

Cliente centralizado sobre `fetch`. Contrato:

- Todos los métodos **resuelven con el JSON ya parseado**; no se llama a `.json()` ni se lee `.ok` sobre el resultado.
- Ante error rechazan con `{ status, message, isCsrf? }`.
- **401:** limpia `usuario` y `sessionUser` de `localStorage` y redirige a `/login.html` (salvo en login, registro, csrf, forgot-password, reset-password y verify-email).
- **403 por CSRF:** refresca el token y reintenta una vez.
- **Timeout:** 15 segundos por defecto; al vencer rechaza con `{ status: 408, message: 'Tiempo de espera agotado' }`.
- Obtiene el token con `GET /api/csrf/` al cargar la página.

```js
PsyAIConnection.get(url, opts)
PsyAIConnection.post(url, body, opts)     // body: objeto (se envía como JSON) o FormData
PsyAIConnection.put(url, body, opts)
PsyAIConnection.patch(url, body, opts)
PsyAIConnection.del(url, opts)
PsyAIConnection.fetchConTimeout(url, options, timeoutMs)
PsyAIConnection.getCsrfToken()            // promesa
PsyAIConnection.refreshCsrfToken()
PsyAIConnection.showChatbotError(mensaje, onRetry)  // diálogo con botón "Reintentar"
```

```js
try {
  const data = await PsyAIConnection.post('/api/chatbot/enviar', { mensaje: texto });
  mostrar(data.respuesta);
} catch (err) {
  PsyAIAlerts.error(err.message);
}
```

### `connection-status.js` y `account-status.js`

- `connection-status.js` solo escucha los eventos `online` y `offline` del navegador y muestra un indicador fijo abajo a la derecha: "Sin conexión" (rojo, parpadeante) o "En línea" (verde, que se oculta a los 3 segundos). No expone una API global.
- `account-status.js` gestiona globalmente el caso de cuenta suspendida (mensaje: "Tu cuenta ha sido suspendida. Contacta al administrador.").

---

## 4. Notificaciones — `PsyAIAlerts`

**Archivo:** `static/js/core/shared/alerts.js` · **Estilos:** `static/css/components/custom-alerts.css`
**Globales:** `window.PsyAIAlerts` y `window.mostrarToast`.

```js
PsyAIAlerts.show({
  type: 'success' | 'error' | 'warning' | 'info' | 'welcome' | 'reminder',
  title: 'Título opcional',
  message: 'Mensaje principal',
  duration: 4000,         // ms; 0 = no se cierra sola
  icon: 'fa-custom-icon'  // opcional, sustituye al icono del tipo
});

PsyAIAlerts.success(message, title)   // título por defecto "¡Éxito!"
PsyAIAlerts.error(message, title)     // dura 5000 ms
PsyAIAlerts.warning(message, title)
PsyAIAlerts.info(message, title)
PsyAIAlerts.welcome(name, role)       // role: 'paciente' por defecto
PsyAIAlerts.reminder(title, message)

mostrarToast(mensaje, tipo, duracion) // API simple heredada
```

Comportamiento:

- Se muestran como máximo **3 alertas a la vez** (`maxTotal`); al superarlo se descartan las más antiguas.
- Los mensajes de más de **150 caracteres** se truncan con `...`.
- Cada alerta lleva una barra de progreso y se adapta sola al modo oscuro (`html.dark-mode`).
- El contenedor se ancla arriba a la derecha (`top: 24px; right: 24px`).

Para diálogos de confirmación se usa **SweetAlert2** (`Swal`), configurado en `head.html`.

---

## 5. Tema claro/oscuro

El modo oscuro se activa con la clase **`dark-mode` en `<html>`**, no con `prefers-color-scheme`.

- **Tokens claros:** `static/css/base/base.css` (`:root`).
- **Tokens oscuros y reglas por componente:** `static/css/themes/theme.css` (`html.dark-mode`), con retoques en `dark-polish.css`.

| Token | Claro | Oscuro |
|---|---|---|
| `--surface-canvas` | `#F7F9FC` | `#0A1220` |
| `--surface-card` | `#FFFFFF` | `#101B2E` |
| `--surface-card-hover` | `#FBFCFE` | `#142238` |
| `--text-primary` | `#0E1B33` | `#EAF1FB` |
| `--text-secondary` | `#4A5B78` | `#A9BAD4` |
| `--text-muted` | `#8494AC` | `#6F84A6` |
| `--brand-500` | `#2F6FE4` | `#4A8AF4` |
| `--border-subtle` | `#E7EDF6` | `#1C2D48` |

### Funcionamiento

1. En el servidor, `index.html` pone `class="dark-mode"` en `<html>` si la cookie `theme` vale `dark`.
2. `theme-inline.js` (en `<head>`, para evitar el parpadeo) añade `dark-mode` si no está: lee la cookie `theme` y, si no existe, `localStorage.theme`. **Si no hay ninguna preferencia guardada, el tema por defecto es oscuro.**
3. `theme.js` alterna la clase al pulsar `#theme-toggle` (con la clase temporal `theme-animating` para la transición), actualiza los iconos `#sun-icon` y `#moon-icon` y el atributo `aria-pressed`.
4. La preferencia se guarda en `localStorage`, en la cookie `theme` (1 año) y en el servidor con `POST /api/theme`.

```html
<div class="theme-switch-container">
  <i class="fa-solid fa-sun theme-icon sun" id="sun-icon"></i>
  <button id="theme-toggle" title="Cambiar modo"></button>
  <i class="fa-solid fa-moon theme-icon moon" id="moon-icon"></i>
</div>
```

---

## 6. Tiempo real

- **Panel de administración:** usa Server-Sent Events (`admin.dashboard.sse.js`) contra `/api/admin/stats/stream` y `/api/admin/logs/stream`; las gráficas se dibujan con Chart.js autoalojado (`admin.dashboard.charts.js`).
- **Chat paciente–profesional (`direct-chat.js`):** usa **sondeo periódico** (`setInterval`) con `GET /api/chat/mensajes/?receptor=<id>&desde=<marca>`, no SSE.

---

## 7. Convenciones

### JavaScript

- JavaScript vanilla (ES6+), sin framework, sin transpilador y sin bundler. Los scripts se cargan con `<script src>`.
- El código compartido son scripts clásicos que cuelgan de un objeto global (`PsyAIAlerts`, `PsyAIConnection`, `CSRF`) o se envuelven en una función autoejecutable. No se usan módulos ES.
- Para llamar a la API usar `PsyAIConnection` (o `fetch`, que ya recibe el CSRF automáticamente).
- `async/await` y `try/catch` con aviso al usuario mediante `PsyAIAlerts`.

### CSS

- Usar los tokens (`var(--surface-card)`, `var(--text-primary)`, …) en lugar de colores fijos; así el modo oscuro funciona solo.
- Nombres de clase estilo BEM (`.sidebar__nav`, `.sidebar__logo-img`).
- El modo oscuro se escribe como `html.dark-mode .componente { … }` o redefiniendo tokens.
- El responsive vive en `static/responsive/`; `responsive-fix.css` se carga al final y tiene la última palabra.
- Los estilos de cada rol se acotan con la clase del `<body>`: `patient-dashboard`, `professional-dashboard` / `aside-professional` y `admin-panel`, para no afectar a otros roles.

### Plantillas

- Plantillas Django con parciales en `templates/base/partials/` (`head.html`, `scripts.html`).
- `{% csrf_token %}` en formularios tradicionales y la meta `csrf-token` para `fetch`.
- Al cambiar un CSS o JS, subir el parámetro `?v=` de su referencia.

---

## 8. Scripts por página

| Página | Scripts específicos (además de `head.html` y `scripts.html`) |
|---|---|
| Landing | `aos.js`, `alerts.js`, `mobile-navbar-toggle.js`, `js/base/index.js` |
| Login | `alerts.js`, `logout.js`, `auth-ui.js`, `login.js` |
| Registro | `alerts.js`, `auth-ui.js`, `register.js` |
| Recuperar / restablecer contraseña | `alerts.js`, `auth-ui.js`, `recover.js` |
| Paciente · chatbot | `auth-guard.js`, `alerts.js`, `patient/aside.js`, `patient/chatbot.js`, `logout.js`, `nombre.usuario.js` |
| Paciente · agenda | `auth-guard.js`, `alerts.js`, `auth-ui.js`, `patient/aside.js`, `custom-select.js`, `patient/agendaquotes.js` |
| Paciente · evolución | `patient/evolution.js` |
| Paciente · historia clínica | `patient/historia_clinica_paciente.js` |
| Paciente · perfil | `patient/my.profile.js` |
| Paciente · mensajes | `shared/direct-chat.js` |
| Paciente · facturas | solo los comunes del portal; la lógica está en un `<script>` dentro de la propia plantilla |
| Profesional · agenda | `professional/aside.js`, `auth-ui.js`, `professional/my.agenda.js` |
| Profesional · pacientes | `professional/anamnesis.js`, `patients.js`, `patients.evolution.js`, `patients.prediagnostico.js` |
| Profesional · facturación | solo los comunes del portal; la lógica está en un `<script>` dentro de la plantilla |
| Profesional · reportes | `professional/reports.js` |
| Profesional · historia clínica | `professional/historia_clinica_pro.js` |
| Profesional · perfil | `professional/my.profile2.js` |
| Profesional · mensajes | `shared/direct-chat.js` |
| Admin · dashboard | `core/shared/aside.js`, `admin.dashboard.utils.js`, `admin.dashboard.sse.js`, `vendor/chart.umd.min.js`, `admin.dashboard.charts.js`, `admin.dashboard.js` |
| Admin · usuarios, roles, notificaciones, configuración del chatbot | `core/shared/aside.js` más su módulo: `admin.users.js`, `admin.roles.js`, `admin.notifications.js`, `admin.chatbot.config.js` |
| Admin · logs | `core/shared/aside.js`, `admin.dashboard.utils.js`, `admin.logs.js`, `admin.rendimiento.js` |
| Admin · facturación | `core/shared/aside.js`; la lógica está en un `<script>` dentro de la plantilla |

Los portales de paciente y profesional comparten `alerts.js`, `logout.js` y `nombre.usuario.js`; el paciente suma además `auth-guard.js`.

---

## 9. Puntos a vigilar

| Tema | Detalle |
|---|---|
| SweetAlert2 por CDN | Es la única librería de UI que no es local; depende de internet y de que la política CSP permita `cdn.jsdelivr.net` |
| Doble manejo de CSRF | `csrf.js` parchea `fetch` y `api-connection.js` gestiona su propio token; conviene unificarlos |
| Archivos sin referencias | `base/landing.js`, `base/hero-carousel.js`, `base/navbar-scroll.js`, `core/shared/scroll-reveal.js`, `css/base/animations.css`, `css/components/cookies.css`, `responsive/auth.css` y `responsive/general.css` no aparecen en ninguna plantilla ni script |
| Copia de respaldo en el repo | `static/css/pages/landing.css.bak-impacto` |
| Dos `aside.js` por rol | Cada portal tiene el suyo, y el de admin vive en `core/shared/`; hay lógica repetida |
| Estilos en línea | `connection-status.js` aplica sus estilos con JavaScript en vez de usar clases |
| Lógica dentro de plantillas | Las páginas de facturas (paciente, profesional y admin) y el formulario del boletín de la landing llevan su JavaScript dentro de la plantilla; conviene moverlo a `static/js/modules/` |
| Chat con sondeo | `direct-chat.js` consulta periódicamente; con muchos usuarios conviene pasar a SSE |

---

## Ver también

- [`API_DOCUMENTATION.md`](../API_DOCUMENTATION.md) — endpoints que consumen estos scripts
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — arquitectura general
- [`data-models.md`](data-models.md) — modelos de datos
- [`chatbot-ai.md`](chatbot-ai.md) — detalle de `chatbot.js`
- [`security.md`](security.md) — CSRF, sesiones y CSP
- [`deployment.md`](deployment.md) — build y estáticos en Docker