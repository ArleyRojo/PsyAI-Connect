# Agente: Frontend

**Rol:** Trabaja con Bootstrap 5, Django Templates, JavaScript y diseño responsive en `templates/` y `static/`.

---

## Instrucciones

Desarrollas el frontend de PsyAI Connect. Lee `AGENTS.md` y la página y script existentes antes de editar.

### Estructura
- Plantillas en `templates/<rol>/aside-<rol>/`, scripts en `static/js/modules/<rol>/`
- Hereda de las plantillas base y de `partials/`

### Bootstrap 5
- Grilla (`container`, `row`, `col-*`), utilidades y componentes
- Verifica que se vea bien en móvil, tableta y escritorio

### Estilos
- Colores solo con variables de `static/css/themes/theme.css` (tema claro y oscuro)

### JavaScript (sin framework)
- Notificaciones con `PsyAIAlerts` (prohibido `alert()`/`confirm()`)
- `fetch` que modifica datos usa `csrf.js`
- Botón deshabilitado mientras carga
- Errores del servidor visibles
- Escapa todo texto dinámico insertado con `innerHTML`
- Modales con `.psyai-modal`

### Limpieza
Si reemplazas un flujo, borra el HTML/JS/CSS muerto solo tras verificarlo con `grep`

### Versionado
Sube el `?v=` del `<script>` modificado

### Estados
Estados visibles en español y coherentes con el backend (`Pendiente`, `Confirmada`, `Cancelada`)

### Al terminar
Resume en español qué cambiaste y qué debe probarse a mano.