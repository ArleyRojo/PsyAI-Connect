# API — PsyAI Connect

Documentación de los endpoints REST de PsyAI Connect. Las rutas, métodos y permisos se obtuvieron del resolvedor de URLs de Django y de las clases de permisos de cada vista; los campos de las peticiones salen de los serializers y servicios. Las descripciones breves de algunas rutas se infieren del nombre de la vista.

- **Prefijo:** todas las rutas de la API cuelgan de `/api/`.
- **Formato:** JSON (`Content-Type: application/json`), salvo las subidas de archivos, que usan `multipart/form-data`.
- **Zona horaria / idioma:** `America/Bogota`, `es-co`.

## 1. Convenciones

### Autenticación y CSRF

La API usa **sesiones** (cookie `sessionid`, `HttpOnly`, 7 días), no tokens.

1. Pedir el token CSRF: `GET /api/csrf/`.
2. Enviarlo en la cabecera `X-CSRFToken` en cada `POST`, `PUT`, `PATCH` y `DELETE`.
3. Iniciar sesión con `POST /api/login`; el navegador conserva la cookie.

La cookie CSRF es `HttpOnly`, por eso el token se obtiene desde `/api/csrf/` y no desde JavaScript.

### Roles

| Valor de `rol` | Clase de permiso |
|---|---|
| `paciente` | `IsPaciente` |
| `profesional` | `IsProfesional` |
| `admin` | `IsAdmin` |

Combinaciones usadas: `IsPacienteOrProfesional`, `IsAdminOrProfesional`, `IsOwnerOrStaff`. `IsAuthenticatedDRF` exige sesión activa y valida que la cuenta exista y esté activa.

En las tablas, la columna **Acceso** indica:

| Etiqueta | Significado |
|---|---|
| Público | Sin autenticación |
| Sesión | Cualquier usuario autenticado |
| Paciente / Profesional / Admin | Solo ese rol |
| Sin clase DRF | La vista no declara permisos DRF; puede ser pública o validar por su cuenta |

### Formato de respuesta

Éxito (el contenido varía por endpoint):

```json
{ "success": true, "message": "Cita agendada correctamente", "idCita": 42 }
```

Error:

```json
{ "success": false, "message": "Descripción del error", "code": 400 }
```

### Códigos HTTP frecuentes

| Código | Cuándo |
|---|---|
| 200 / 201 | Operación correcta / recurso creado |
| 400 | Datos inválidos o incompletos |
| 401 | No autenticado o credenciales incorrectas |
| 403 | Rol sin permiso, cuenta suspendida, o recurso de otro usuario |
| 404 | Recurso no encontrado |
| 429 | Demasiados intentos (login, registro, recuperación) o límite de peticiones |
| 500 | Error interno |

### Límites de peticiones

DRF aplica `60/minuto` a usuarios anónimos y `120/minuto` a autenticados. Además, el login bloquea temporalmente tras intentos fallidos (responde 429 con `retry_after` en segundos) y el registro y la recuperación de contraseña tienen su propio límite por correo.

### Paginación y filtros

Donde existe paginación se usan `page` y `limit` (por defecto `limit=20` en la agenda del profesional).

---

## 2. Autenticación

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/csrf/` | Público | Devuelve el token CSRF |
| POST | `/api/register` | Público | Registro de paciente o profesional |
| POST | `/api/login` | Público | Inicio de sesión |
| POST | `/api/logout` | Público | Cierra la sesión |
| GET | `/api/session` | Público | Estado de la sesión actual |
| POST | `/api/forgot-password` | Público | Solicita el correo de recuperación |
| POST | `/api/reset-password` | Público | Cambia la contraseña con el token recibido |
| POST | `/api/verify-email` | Público | Verifica el correo con el token recibido |
| GET | `/api/social-redirect` | — | Redirección posterior al login con Google |
| GET | `/api/totp/status` | Sesión | Estado del 2FA |
| GET | `/api/totp/setup` | Sesión | Inicia la configuración del 2FA (`?name=`) |
| POST | `/api/totp/confirm` | Sesión | Confirma el 2FA con un código |
| POST | `/api/totp/disable` | Sesión | Desactiva el 2FA (pide la contraseña) |
| POST | `/api/totp/verify-login` | Público | Segundo paso del login cuando hay 2FA |

El inicio de sesión con Google se hace con django-allauth bajo `/accounts/`.

> El 2FA depende de la librería `pyotp`, que no figura en `requirements.txt`; sin ella estos endpoints no funcionan.

### POST `/api/register`

```json
{
  "nombre": "Ana Torres",
  "email": "ana@correo.com",
  "password": "Clave123",
  "confirm_password": "Clave123",
  "rol": "paciente",
  "genero": "femenino",
  "fecha_nacimiento": "1995-04-12",
  "acepta_terminos": true
}
```

- `rol`: `paciente` (por defecto) o `profesional`.
- La contraseña debe tener al menos 6 caracteres, una mayúscula y un número.
- Edad mínima: 18 años (`EDAD_MINIMA_REGISTRO`).
- Errores: 400 (validación), 429 (límite de intentos).

### POST `/api/login`

```json
{ "email": "ana@correo.com", "password": "Clave123", "rol": "paciente" }
```

- `rol` es opcional (`paciente` por defecto) y debe coincidir con el rol real de la cuenta, o responde 403.
- Respuesta correcta: `success`, `message` y la página a la que redirigir según el rol.
- Si la cuenta tiene 2FA activo responde `{"success": true, "requires_2fa": true, "user_id": …}` y hay que llamar a `/api/totp/verify-login` con `{"token": "123456"}`.
- Errores: 401 (credenciales), 403 (rol incorrecto o cuenta suspendida), 429 (bloqueo temporal).

### POST `/api/forgot-password` · `/api/reset-password` · `/api/verify-email`

```json
{ "email": "ana@correo.com" }
```
```json
{ "token": "…", "new_password": "NuevaClave1", "confirm_password": "NuevaClave1" }
```
```json
{ "token": "…" }
```

### GET `/api/session`

Devuelve `logged_in`, `usuario` (`idUsuario`, `nombre`, `rol`) y `fotoPerfil`.

---

## 3. Pacientes

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/pacientes/` | Admin o Profesional | Lista de pacientes (`page`, `limit`) |
| GET, PUT | `/api/perfil/paciente/<id>` | Sesión | Ver o actualizar el perfil del paciente |
| POST, PUT | `/api/perfil/foto` · `/api/perfil/paciente/foto` | Sesión | Sube la foto de perfil |
| GET | `/api/preferencias/paciente/` | Paciente | Preferencias (`notificaciones`, `tema`, `idioma`) |
| PUT | `/api/preferencias/paciente/<id>/` | Paciente | Actualiza las preferencias |
| GET | `/api/profesionales/` | Sesión | Lista de profesionales |
| GET, POST | `/api/evolucion/` · `/api/evolución` | Paciente | Registro y consulta de evolución (`fecha`, …) |
| GET, POST, PUT, DELETE | `/api/paciente/<id>/anamnesis/` | Admin o Profesional | Historia clínica inicial del paciente |
| GET | `/api/paciente/mis-datos` | Paciente | Exporta los datos personales |
| GET | `/api/paciente/consentimientos` | Paciente | Consentimientos otorgados |
| POST | `/api/paciente/consentimientos/revocar` | Paciente | Revoca un consentimiento |
| GET | `/api/paciente/solicitudes-derechos` | Paciente | Solicitudes de derechos sobre sus datos |
| POST | `/api/cuenta/eliminar` | Paciente | Solicita la eliminación de la cuenta |
| GET, POST | `/api/paciente/documentos` · `/api/paciente/documentos/` | Paciente | Lista o sube documentos propios |
| POST | `/api/paciente/documentos/subir` | Paciente | Sube un documento (`archivo`, `descripcion`) |
| PATCH, DELETE | `/api/paciente/documentos/<pk>/` | Paciente | Edita o elimina un documento propio |

---

## 4. Profesionales

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/perfil/profesional/<id>` | Sesión | Perfil público de un profesional |
| PUT | `/api/perfil/profesional` | Sesión | Actualiza el perfil (`especialidad`, `experiencia`, …) |
| GET | `/api/profesional/dashboard` | Profesional | Resumen del panel |
| GET | `/api/profesional/pacientes` | Profesional | Pacientes asignados |
| GET | `/api/profesional/pacientes/todos` | Sesión | Todos los pacientes disponibles |
| POST | `/api/profesional/pacientes/<id>/asignar` | Profesional | Asigna un paciente al profesional |
| GET | `/api/profesional/paciente/<id>/chatbot-historial` · `/api/profesional/pacientes/<id>/chatbot/historial` | Sesión | Historial del chatbot de un paciente |
| GET | `/api/evolucion/profesional` | Profesional | Evolución de sus pacientes |
| GET | `/api/prediagnosticos/profesional` | Profesional | Prediagnósticos generados por el chatbot |
| GET, POST | `/api/diagnosticos` | Profesional | Lista o crea diagnósticos |
| GET, POST | `/api/reportes` | Profesional | Lista o crea reportes |
| GET | `/api/reportes/profesional` · `/api/reportes/eliminados` | Profesional | Reportes propios / eliminados |
| PUT, DELETE | `/api/reportes/<id>` | Profesional | Actualiza (`estado`) o elimina un reporte |
| GET, POST | `/api/disponibilidad` | Sesión | Lista o crea disponibilidad |
| GET | `/api/disponibilidad/<id>` | Sesión | Consulta una disponibilidad |
| GET, PUT | `/api/profesional/payment-info` | Profesional | Datos de cobro propios (`qr_image`, `mensaje_texto`) |
| GET | `/api/profesional/<id>/payment-info` | Sesión | Datos de cobro públicos de un profesional |
| GET, POST | `/api/profesional/chat/mensajes` · `/api/profesional/chat/enviar` | Profesional | Mensajes con pacientes |
| GET | `/api/chat/pacientes` | Profesional | Contactos del chat |
| GET, POST | `/api/profesional/pacientes/<id>/documentos` · `/api/profesional/paciente/<id>/documentos` | Profesional | Documentos del profesional para un paciente |
| PUT, PATCH, DELETE | `/api/profesional/documentos/<id>` | Profesional | Edita o elimina un documento |
| PATCH, PUT | `/api/profesional/documentos/<id>/visibilidad` | Profesional | Cambia la visibilidad para el paciente |
| GET | `/api/descargar/documento-paciente/<id>` · `/api/descargar/documento-profesional/<id>` · `/api/descargar/<tipo>/<id>` | Sesión | Descarga de documentos |
| GET | `/api/admin/profesionales/pendientes` | Admin | Profesionales pendientes de verificación |
| POST | `/api/admin/profesionales/<id>/verificar` · `/desverificar` | Admin | Verifica o retira la verificación |

### POST `/api/diagnosticos`

```json
{
  "idPaciente": 12,
  "sintomas": "…",
  "diagnostico": "…",
  "tratamiento": "…",
  "fecha_diagnostico": "2026-10-30"
}
```

Solo `idPaciente` es obligatorio. El profesional debe tener relación con el paciente.

### POST `/api/disponibilidad`

```json
{ "fecha": "2026-11-10", "horaInicio": "08:00", "horaFin": "12:00" }
```

También acepta `dia`, `hora_inicio` y `hora_fin`. No se permiten fechas pasadas.

---

## 5. Citas

Estados válidos: `Pendiente`, `Confirmada`, `Completada`, `Cancelada`.

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET, POST | `/api/citas/` | Sesión | Lista las citas del usuario o crea una |
| GET | `/api/citas/paciente` · `/api/citas/profesional` | Sesión | Lista según el rol |
| PATCH, DELETE | `/api/citas/<id>` | Sesión | Cambia el estado o cancela |
| GET | `/api/citas/proxima` · `/api/citas/próxima` | Paciente | Próxima cita del paciente |
| GET | `/api/citas/disponibles` | Público | Horarios libres (`idProfesional`, `fecha`) |
| GET | `/api/citas/fechas-disponibles` | Público | Fechas con disponibilidad (`idProfesional`, `anio`, `mes`) |
| GET | `/api/citas/horarios-ocupados` | Profesional | Horarios ocupados (`idProfesional`, `fecha`) |

### POST `/api/citas/`

```json
{
  "idProfesional": 7,
  "fecha": "2026-11-10",
  "hora": "09:00",
  "motivo": "Ansiedad",
  "tipoCita": "Virtual",
  "creado_por_profesional": false,
  "idPaciente": 12
}
```

- `idProfesional`, `fecha` y `hora` son obligatorios. `idPaciente` solo se usa si la crea el profesional.
- No se pueden agendar citas en el pasado (400).
- Respuesta: `{"success": true, "message": "Cita agendada correctamente", "idCita": 42}`.
- Crear una cita **no genera factura**.

### PATCH `/api/citas/<id>`

```json
{ "estado": "Confirmada", "monto": 100000, "descripcion": "Cita virtual" }
```

- `monto` y `descripcion` son opcionales y solo se leen al confirmar.
- Al pasar a `Confirmada` se crea, dentro de una transacción, una factura en estado `Pendiente` si no existe. Si no se envía `monto`, se usa `CITA_MONTO_DEFAULT` (100000 por defecto).
- Un profesional solo puede cambiar sus propias citas (403 si no), y no se puede confirmar una cita pasada.

### DELETE `/api/citas/<id>`

```json
{ "motivoCancelacion": "No puedo asistir" }
```

---

## 6. Facturación

Los cobros son manuales: la factura queda `Pendiente` al confirmar la cita y pasa a `Pagado` cuando el profesional adjunta la evidencia.

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET, POST | `/api/facturas` | Sesión | Lista según el rol o crea una factura |
| GET | `/api/facturas/mias` | Sesión | Facturas propias |
| GET | `/api/facturas/emitidas` | Sesión | Facturas emitidas |
| GET | `/api/facturas/stats` · `/api/facturas/estadisticas-admin` | Sesión | Estadísticas según el rol |
| GET | `/api/facturas/pacientes-profesional` | Profesional | Pacientes a los que puede facturar |
| GET, PATCH | `/api/facturas/<id>` | Sesión | Consulta o actualiza (anular, `estadoPago`) |
| POST | `/api/facturas/<id>/confirmar-pago` | Profesional | Marca como pagada subiendo la evidencia |
| GET | `/api/facturas/<id>/evidencia` | Sesión | Descarga la evidencia del pago |

Filtros del listado: `estado`, `profesional`, `paciente`, `fecha_desde`, `fecha_hasta` (según el rol).

### POST `/api/facturas` (multipart)

Campos: `idPaciente`, `idCita` (opcional), `items` y los datos del pago (`fechaPago`, `metodoPago`, `referencia`, `notas`) más el archivo `evidencia`.

```json
{
  "idPaciente": 12,
  "idCita": 42,
  "items": [{ "descripcion": "Cita virtual", "precioUnitario": "100000" }]
}
```

- El profesional debe tener relación con el paciente (403 si no).
- `fechaPago` no puede ser futura.
- La evidencia es obligatoria y solo admite `jpg`, `jpeg`, `png`, `webp` o `pdf`.
- Se crea en estado `Pagado`, y se envía un correo al paciente. Respuesta 201 con `idFactura`.

### POST `/api/facturas/<id>/confirmar-pago` (multipart)

Campos: `evidencia` (obligatorio), `metodoPago`, `referencia`, `notas`.

Errores: 400 (ya pagada, anulada o sin evidencia), 403 (la factura no es del profesional), 404.

### PATCH `/api/facturas/<id>`

```json
{ "anular": true, "motivoAnulacion": "Duplicada" }
```

---

## 7. Chatbot y chat

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET, POST | `/api/chatbot/` | Paciente | Historial / envía un mensaje al chatbot |
| POST | `/api/chatbot/enviar` | Paciente | Envía un mensaje (ruta heredada) |
| GET, DELETE | `/api/chatbot/historial` | Paciente | Consulta o borra el historial |
| DELETE | `/api/chatbot/<pk>/` | Paciente | Elimina una conversación |
| GET | `/api/chatbot/config/` | Paciente | Configuración visible del chatbot |
| GET | `/api/chatbot/config/events` | Sin clase DRF | Flujo de eventos de configuración |
| POST | `/api/chatbot/encuesta/` | Paciente | Encuesta de satisfacción |
| POST | `/api/chatbot/prediagnostico/` | Paciente | Genera un prediagnóstico |
| GET, POST | `/api/paciente/consentimiento-chatbot/` | Paciente | Consulta o registra el consentimiento |
| GET | `/api/chat/contactos/` · `/api/chat/profesionales` | Paciente | Profesionales con los que puede chatear |
| GET, POST | `/api/chat/mensajes/` · `/api/paciente/chat/mensajes` | Sesión | Mensajes paciente–profesional |
| POST | `/api/chat/enviar` · `/api/paciente/chat/enviar` | Sesión | Envía un mensaje |
| DELETE | `/api/chat/historial/<pk>/` | Paciente | Elimina una conversación del chat |

### POST `/api/chatbot/enviar`

```json
{ "mensaje": "Me siento muy ansioso hoy" }
```

La respuesta incluye el campo `respuesta` con el texto del chatbot. Si detecta riesgo alto o crítico, el texto incluye la línea de crisis configurada y se puede enviar una alerta por correo.

### POST `/api/chatbot/encuesta/`

```json
{ "utilidad": true, "claridad": true, "recomendaria": "si", "comentario": "…" }
```

`recomendaria` es una opción de lista (ver `ChatbotEncuestaSerializer`).

### POST `/api/chat/mensajes/`

```json
{ "receptor": 7, "mensaje": "Hola, ¿podemos reagendar?" }
```

Para consultar: `GET /api/chat/mensajes/?receptor=7&desde=<marca>`.

> Varias rutas del chat y del chatbot están registradas tanto en la app `patients` como en `chatbot`; hay rutas heredadas (`*_legacy`) y alias con acento (`/api/evolución`, `/api/citas/próxima`).

---

## 8. Documentos

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET, POST | `/api/documentos/paciente` | Sesión | Lista o sube documentos del paciente |
| GET | `/api/documentos/paciente/dashboard` | Sesión | Resumen de documentos |
| DELETE | `/api/documentos/paciente/doc/<id>` | Sesión | Elimina un documento propio |
| GET | `/api/documentos/paciente/doc/<id>/descargar` | Sesión | Descarga |
| POST | `/api/documentos/autorizacion/<id>` | Paciente | Autoriza o revoca el acceso del profesional |
| GET, POST | `/api/documentos/profesional/<id_paciente>` | Sesión | Documentos que el profesional comparte con un paciente |
| PATCH, DELETE | `/api/documentos/profesional/doc/<id>` | Sesión | Edita o elimina |
| GET | `/api/documentos/profesional/doc/<id>/descargar` | Sesión | Descarga |

Subida de documento de paciente (multipart): `archivo`, `descripcion`. De profesional: `archivo`, `categoria`, `visibilidad`, `notas`. Las extensiones y el tamaño máximo los controlan `ALLOWED_UPLOAD_EXTENSIONS` (por defecto `jpg, jpeg, png, pdf, gif, webp, doc, docx`) y `MAX_UPLOAD_SIZE_MB` (por defecto 5).

---

## 9. Administración

Todas exigen sesión con rol `admin`, salvo donde se indica.

| Método | Ruta | Descripción |
|---|---|---|
| GET, POST | `/api/admin/usuarios` | Lista o crea usuarios |
| GET, PUT, PATCH, DELETE | `/api/admin/usuarios/<pk>` | Consulta, edita, bloquea o desbloquea y elimina |
| GET | `/api/admin/stats` | Estadísticas del sistema |
| GET | `/api/admin/stats/stream` | Estadísticas en tiempo real (SSE) |
| GET | `/api/admin/logs` | Registros del sistema |
| GET | `/api/admin/logs/stream` | Registros en tiempo real (SSE, con heartbeat) |
| GET | `/api/admin/online` | Usuarios conectados |
| GET | `/api/admin/roles/usuarios` · `/api/admin/roles/historial` | Roles y su historial |
| GET, POST, DELETE | `/api/admin/notificaciones` · `/api/admin/notificaciones/<id>` | Notificaciones del panel |
| GET, POST | `/api/admin/chatbot-config` | Configuración del chatbot |
| PUT, PATCH, DELETE | `/api/admin/chatbot-config/<pk>` | Edita o elimina una configuración |
| GET | `/api/admin/chatbot-config/palabras-detectadas` | Palabras detectadas por el chatbot |
| GET | `/api/admin/chatbot-historial` | Historial del chatbot (`nivel`, `q`) |
| POST | `/api/admin/crear-columnas-diagnostico` | Utilidad de mantenimiento |

---

## 10. Utilidades y salud

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/health/` · `/healthz/` (también `/api/health/`, `/api/healthz/`) | Público | Estado del servicio |
| GET, POST | `/api/theme` | Sin clase DRF | Preferencia de tema |
| GET, POST | `/api/newsletter/subscribe` | Sin clase DRF | Suscripción al boletín |
| GET, POST | `/api/client-errors` | Sin clase DRF | Registro de errores del navegador |
| GET, POST | `/api/config/pago/` | Sin clase DRF | Datos del link de cobro (`PAGO_CUENTA_URL`, `PAGO_CUENTA_NOMBRE`) |
| POST | `/api/whatsapp/webhook/` | Sin clase DRF | Webhook entrante de WhatsApp (Twilio) |
| GET | `/media/qr_codes/<archivo>` | Público | QR de cobro de profesionales |

---

## 11. Notas de seguridad de la API

- Los endpoints de **citas disponibles** (`/api/citas/disponibles` y `/api/citas/fechas-disponibles`) no exigen autenticación.
- Varias rutas de utilidades (`config/pago`, `newsletter`, `client-errors`, `theme`, `whatsapp/webhook`) no declaran clases de permisos DRF; conviene confirmar que cada una valida lo necesario por su cuenta.
- No hay documentación OpenAPI generada automáticamente. Una opción es añadir `drf-spectacular` para exponerla en `/api/docs/`.

---

## English Version

# API — PsyAI Connect

Documentation of PsyAI Connect REST endpoints. Routes, methods, and permissions were obtained from the Django URL resolver and from the permission classes of each view; brief descriptions of some routes are inferred from the view name.

- **Prefix:** all API routes hang under `/api/`.
- **Format:** JSON (`Content-Type: application/json`), except file uploads, which use `multipart/form-data`.
- **Timezone / language:** `America/Bogota`, `es-co`.

## 1. Conventions / Convenciones

### Authentication and CSRF / Autenticación y CSRF

The API uses **sessions** (cookie `sessionid`, `HttpOnly`, 7 days), not tokens.

1. Request the CSRF token: `GET /api/csrf/`.
2. Send it in the header `X-CSRFToken` on every `POST`, `PUT`, `PATCH`, and `DELETE`.
3. Log in with `POST /api/login`; the browser keeps the cookie.

The CSRF cookie is `HttpOnly`, so the token is obtained from `/api/csrf/` and not from JavaScript.

### Roles / Roles

| Value of `rol` | Permission class |
|---|---|
| `paciente` | `IsPaciente` |
| `profesional` | `IsProfesional` |
| `admin` | `IsAdmin` |

Combinations used: `IsPacienteOrProfesional`, `IsAdminOrProfesional`, `IsOwnerOrStaff`. `IsAuthenticatedDRF` requires active session and validates that the account exists and is active.

In tables, the column **Access** indicates:

| Label | Meaning |
|---|---|
| Public | No authentication |
| Session | Any authenticated user |
| Patient / Professional / Admin | Only that role |
| No DRF class | The view does not declare DRF permissions; it may be public or validate on its own |

### Response format / Formato de respuesta

Success (content varies by endpoint):

```json
{ "success": true, "message": "Cita agendada correctamente", "idCita": 42 }
```

Error:

```json
{ "success": false, "message": "Descripción del error", "code": 400 }
```

### Frequent HTTP codes / Códigos HTTP frecuentes

| Code | When |
|---|---|
| 200 / 201 | Successful operation / resource created |
| 400 | Invalid or incomplete data |
| 401 | Not authenticated or incorrect credentials |
| 403 | Role without permission, suspended account, or resource belonging to another user |
| 404 | Resource not found |
| 429 | Too many attempts (login, registration, recovery) or request limit |
| 500 | Internal error |

### Rate limits / Límites de peticiones

DRF applies `60/minute` to anonymous users and `120/minute` to authenticated users. Additionally, login temporarily blocks after failed attempts (responds 429 with `retry_after` in seconds) and registration and password recovery have their own per-email limit.

## 2. Authentication / Autenticación

| Method | Route | Access | Description |
|---|---|---|---|
| GET | `/api/csrf/` | Public | Returns the CSRF token |
| POST | `/api/register` | Public | Patient or professional registration |
| POST | `/api/login` | Public | Login |
| POST | `/api/logout` | Public | Closes the session |
| GET | `/api/session` | Public | Current session status |
| POST | `/api/forgot-password` | Public | Requests recovery email |
| POST | `/api/reset-password` | Public | Changes password with received token |
| POST | `/api/verify-email` | Public | Verifies email with received token |
| GET | `/api/social-redirect` | — | Redirect after Google login |
| GET | `/api/totp/status` | Session | 2FA status |
| GET | `/api/totp/setup` | Session | Starts 2FA setup (`?name=`) |
| POST | `/api/totp/confirm` | Session | Confirms 2FA with a code |
| POST | `/api/totp/disable` | Session | Disables 2FA (asks for password) |
| POST | `/api/totp/verify-login` | Public | Second login step when 2FA is enabled |

Google login is done with django-allauth under `/accounts/`.

> 2FA depends on the `pyotp` library, which is not in `requirements.txt`; without it these endpoints do not work.

### POST `/api/register`

```json
{
  "nombre": "Ana Torres",
  "email": "ana@correo.com",
  "password": "Clave123",
  "confirm_password": "Clave123",
  "rol": "paciente",
  "genero": "femenino",
  "fecha_nacimiento": "1995-04-12",
  "acepta_terminos": true
}
```

- `rol`: `paciente` (default) or `profesional`.
- Password must have at least 6 characters, one uppercase, and one number.
- Minimum age: 18 years (`EDAD_MINIMA_REGISTRO`).
- Errors: 400 (validation), 429 (attempt limit).

### POST `/api/login`

```json
{ "email": "ana@correo.com", "password": "Clave123", "rol": "paciente" }
```

- `rol` is optional (`paciente` by default) and must match the account's real role, or responds 403.
- Correct response: `success`, `message`, and the page to redirect to according to role.
- If the account has 2FA active responds `{"success": true, "requires_2fa": true, "user_id": …}` and you must call `/api/totp/verify-login` with `{"token": "123456"}`.
- Errors: 401 (credentials), 403 (incorrect role or suspended account), 429 (temporary block).

### POST `/api/forgot-password` · `/api/reset-password` · `/api/verify-email`

```json
{ "email": "ana@correo.com" }
```
```json
{ "token": "…", "new_password": "NuevaClave1", "confirm_password": "NuevaClave1" }
```
```json
{ "token": "…" }
```

### GET `/api/session`

Returns `logged_in`, `usuario` (`idUsuario`, `nombre`, `rol`) and `fotoPerfil`.

## 3. Patients / Pacientes

| Method | Route | Access | Description |
|---|---|---|---|
| GET | `/api/pacientes/` | Admin or Professional | List of patients (`page`, `limit`) |
| GET, PUT | `/api/perfil/paciente/<id>` | Session | View or update patient profile |
| POST, PUT | `/api/perfil/foto` · `/api/perfil/paciente/foto` | Session | Upload profile photo |
| GET | `/api/preferencias/paciente/` | Patient | Preferences (`notificaciones`, `tema`, `idioma`) |
| PUT | `/api/preferencias/paciente/<id>/` | Patient | Update preferences |
| GET | `/api/profesionales/` | Session | List of professionals |
| GET, POST | `/api/evolucion/` · `/api/evolución` | Patient | Record and query evolution (`fecha`, …) |
| GET, POST, PUT, DELETE | `/api/paciente/<id>/anamnesis/` | Admin or Professional | Patient's initial clinical history |
| GET | `/api/paciente/mis-datos` | Patient | Exports personal data |
| GET | `/api/paciente/consentimientos` | Patient | Granted consents |
| POST | `/api/paciente/consentimientos/revocar` | Patient | Revokes a consent |
| GET | `/api/paciente/solicitudes-derechos` | Patient | Data rights requests |
| POST | `/api/cuenta/eliminar` | Patient | Requests account deletion |
| GET, POST | `/api/paciente/documentos` · `/api/paciente/documentos/` | Patient | Lists or uploads own documents |
| POST | `/api/paciente/documentos/subir` | Patient | Uploads a document (`archivo`, `descripcion`) |
| PATCH, DELETE | `/api/paciente/documentos/<pk>/` | Patient | Edits or deletes own document |

## 4. Professionals / Profesionales

| Method | Route | Access | Description |
|---|---|---|---|
| GET | `/api/perfil/profesional/<id>` | Session | Public profile of a professional |
| PUT | `/api/perfil/profesional` | Session | Updates profile (`especialidad`, `experiencia`, …) |
| GET | `/api/profesional/dashboard` | Professional | Dashboard summary |
| GET | `/api/profesional/pacientes` | Professional | Assigned patients |
| GET | `/api/profesional/pacientes/todos` | Session | All available patients |
| POST | `/api/profesional/pacientes/<id>/asignar` | Professional | Assigns a patient to the professional |
| GET | `/api/profesional/paciente/<id>/chatbot-historial` · `/api/profesional/pacientes/<id>/chatbot/historial` | Session | Chatbot history of a patient |
| GET | `/api/evolucion/profesional` | Professional | Evolution of their patients |
| GET | `/api/prediagnosticos/profesional` | Professional | Prediagnoses generated by chatbot |
| GET, POST | `/api/diagnosticos` | Professional | Lists or creates diagnoses |
| GET, POST | `/api/reportes` | Professional | Lists or creates reports |
| GET | `/api/reportes/profesional` · `/api/reportes/eliminados` | Professional | Own reports / deleted reports |
| PUT, DELETE | `/api/reportes/<id>` | Professional | Updates (`estado`) or deletes a report |
| GET, POST | `/api/disponibilidad` | Session | Lists or creates availability |
| GET | `/api/disponibilidad/<id>` | Session | Queries an availability |
| GET, PUT | `/api/profesional/payment-info` | Professional | Own payment data (`qr_image`, `mensaje_texto`) |
| GET | `/api/profesional/<id>/payment-info` | Session | Public payment data of a professional |
| GET, POST | `/api/profesional/chat/mensajes` · `/api/profesional/chat/enviar` | Professional | Messages with patients |
| GET | `/api/chat/pacientes` | Professional | Chat contacts |
| GET, POST | `/api/profesional/pacientes/<id>/documentos` · `/api/profesional/paciente/<id>/documentos` | Professional | Professional's documents for a patient |
| PUT, PATCH, DELETE | `/api/profesional/documentos/<id>` | Professional | Edits or deletes a document |
| PATCH, PUT | `/api/profesional/documentos/<id>/visibilidad` | Professional | Changes visibility for patient |
| GET | `/api/descargar/documento-paciente/<id>` · `/api/descargar/documento-profesional/<id>` · `/api/descargar/<tipo>/<id>` | Session | Document download |
| GET | `/api/admin/profesionales/pendientes` | Admin | Professionals pending verification |
| POST | `/api/admin/profesionales/<id>/verificar` · `/desverificar` | Admin | Verifies or removes verification |

### POST `/api/diagnosticos`

```json
{
  "idPaciente": 12,
  "sintomas": "…",
  "diagnostico": "…",
  "tratamiento": "…",
  "fecha_diagnostico": "2026-10-30"
}
```

Only `idPaciente` is mandatory. The professional must have a relationship with the patient.

### POST `/api/disponibilidad`

```json
{ "fecha": "2026-11-10", "horaInicio": "08:00", "horaFin": "12:00" }
```

Also accepts `dia`, `hora_inicio` and `hora_fin`. Past dates are not allowed.

## 5. Appointments / Citas

Valid states: `Pendiente`, `Confirmada`, `Completada`, `Cancelada`.

| Method | Route | Access | Description |
|---|---|---|---|
| GET, POST | `/api/citas/` | Session | Lists user's appointments or creates one |
| GET | `/api/citas/paciente` · `/api/citas/profesional` | Session | Lists according to role |
| PATCH, DELETE | `/api/citas/<id>` | Session | Changes status or cancels |
| GET | `/api/citas/proxima` · `/api/citas/próxima` | Patient | Patient's next appointment |
| GET | `/api/citas/disponibles` | Public | Free slots (`idProfesional`, `fecha`) |
| GET | `/api/citas/fechas-disponibles` | Public | Dates with availability (`idProfesional`, `anio`, `mes`) |
| GET | `/api/citas/horarios-ocupados` | Professional | Occupied slots (`idProfesional`, `fecha`) |

### POST `/api/citas/`

```json
{
  "idProfesional": 7,
  "fecha": "2026-11-10",
  "hora": "09:00",
  "motivo": "Ansiedad",
  "tipoCita": "Virtual",
  "creado_por_profesional": false,
  "idPaciente": 12
}
```

- `idProfesional`, `fecha` and `hora` are mandatory. `idPaciente` is only used if created by the professional.
- Past appointments cannot be scheduled (400).
- Response: `{"success": true, "message": "Cita agendada correctamente", "idCita": 42}`.
- Creating an appointment **does not generate an invoice**.

### PATCH `/api/citas/<id>`

```json
{ "estado": "Confirmada", "monto": 100000, "descripcion": "Cita virtual" }
```

- `monto` and `descripcion` are optional and only read when confirming.
- When changing to `Confirmada` an invoice in `Pendiente` state is created within a transaction if it does not exist. If `monto` is not sent, `CITA_MONTO_DEFAULT` (100000 by default) is used.
- A professional can only change their own appointments (403 otherwise), and a past appointment cannot be confirmed.

### DELETE `/api/citas/<id>`

```json
{ "motivoCancelacion": "No puedo asistir" }
```

## 6. Billing / Facturación

Collections are manual: the invoice remains `Pendiente` when the appointment is confirmed and changes to `Pagado` when the professional attaches evidence.

| Method | Route | Access | Description |
|---|---|---|---|
| GET, POST | `/api/facturas` | Session | Lists according to role or creates an invoice |
| GET | `/api/facturas/mias` | Session | Own invoices |
| GET | `/api/facturas/emitidas` | Session | Issued invoices |
| GET | `/api/facturas/stats` · `/api/facturas/estadisticas-admin` | Session | Statistics according to role |
| GET | `/api/facturas/pacientes-profesional` | Professional | Patients the professional can invoice |
| GET, PATCH | `/api/facturas/<id>` | Session | Queries or updates (void, `estadoPago`) |
| POST | `/api/facturas/<id>/confirmar-pago` | Professional | Marks as paid uploading evidence |
| GET | `/api/facturas/<id>/evidencia` | Session | Downloads payment evidence |

List filters: `estado`, `profesional`, `paciente`, `fecha_desde`, `fecha_hasta` (according to role).

### POST `/api/facturas` (multipart)

Fields: `idPaciente`, `idCita` (optional), `items` and payment data (`fechaPago`, `metodoPago`, `referencia`, `notas`) plus file `evidencia`.

```json
{
  "idPaciente": 12,
  "idCita": 42,
  "items": [{ "descripcion": "Cita virtual", "precioUnitario": "100000" }]
}
```

- The professional must have a relationship with the patient (403 otherwise).
- `fechaPago` cannot be future.
- Evidence is mandatory and only accepts `jpg`, `jpeg`, `png`, `webp` or `pdf`.
- Created in `Pagado` state, and an email is sent to the patient. Response 201 with `idFactura`.

### POST `/api/facturas/<id>/confirmar-pago` (multipart)

Fields: `evidencia` (mandatory), `metodoPago`, `referencia`, `notas`.

Errors: 400 (already paid, voided or no evidence), 403 (invoice is not from the professional), 404.

### PATCH `/api/facturas/<id>`

```json
{ "anular": true, "motivoAnulacion": "Duplicada" }
```

## 7. Chatbot and chat / Chatbot y chat

| Method | Route | Access | Description |
|---|---|---|---|
| GET, POST | `/api/chatbot/` | Patient | History / sends a message to chatbot |
| POST | `/api/chatbot/enviar` | Patient | Sends a message (legacy route) |
| GET, DELETE | `/api/chatbot/historial` | Patient | Queries or deletes history |
| DELETE | `/api/chatbot/<pk>/` | Patient | Deletes a conversation |
| GET | `/api/chatbot/config/` | Patient | Visible chatbot configuration |
| GET | `/api/chatbot/config/events` | No DRF class | Chatbot configuration event stream |
| POST | `/api/chatbot/encuesta/` | Patient | Satisfaction survey |
| POST | `/api/chatbot/prediagnostico/` | Patient | Generates a prediagnosis |
| GET, POST | `/api/paciente/consentimiento-chatbot/` | Patient | Queries or registers consent |
| GET | `/api/chat/contactos/` · `/api/chat/profesionales` | Patient | Professionals the patient can chat with |
| GET, POST | `/api/chat/mensajes/` · `/api/paciente/chat/mensajes` | Session | Patient–professional messages |
| POST | `/api/chat/enviar` · `/api/paciente/chat/enviar` | Session | Sends a message |
| DELETE | `/api/chat/historial/<pk>/` | Patient | Deletes a chat conversation |

### POST `/api/chatbot/enviar`

```json
{ "mensaje": "Me siento muy ansioso hoy" }
```

The response includes the `respuesta` field with the chatbot's text. If high or critical risk is detected, the text includes the configured crisis line and an email alert can be sent.

### POST `/api/chatbot/encuesta/`

```json
{ "utilidad": true, "claridad": true, "recomendaria": "si", "comentario": "…" }
```

`recomendaria` is a list option (see `ChatbotEncuestaSerializer`).

### POST `/api/chat/mensajes/`

```json
{ "receptor": 7, "mensaje": "Hola, ¿podemos reagendar?" }
```

To query: `GET /api/chat/mensajes/?receptor=7&desde=<marca>`.

> Several chat and chatbot routes are registered both in the `patients` app and in `chatbot`; there are legacy routes (`*_legacy`) and accented aliases (`/api/evolución`, `/api/citas/próxima`).

## 8. Documents / Documentos

| Method | Route | Access | Description |
|---|---|---|---|
| GET, POST | `/api/documentos/paciente` | Session | Lists or uploads patient documents |
| GET | `/api/documentos/paciente/dashboard` | Session | Document summary |
| DELETE | `/api/documentos/paciente/doc/<id>` | Session | Deletes own document |
| GET | `/api/documentos/paciente/doc/<id>/descargar` | Session | Download |
| POST | `/api/documentos/autorizacion/<id>` | Patient | Authorizes or revokes professional access |
| GET, POST | `/api/documentos/profesional/<id_paciente>` | Session | Documents the professional shares with a patient |
| PATCH, DELETE | `/api/documentos/profesional/doc/<id>` | Session | Edits or deletes |
| GET | `/api/documentos/profesional/doc/<id>/descargar` | Session | Download |

Patient document upload (multipart): `archivo`, `descripcion`. From professional: `archivo`, `categoria`, `visibilidad`, `notas`. Extensions and maximum size are controlled by `ALLOWED_UPLOAD_EXTENSIONS` (default `jpg, jpeg, png, pdf, gif, webp, doc, docx`) and `MAX_UPLOAD_SIZE_MB` (default 5).

## 9. Administration / Administración

All require session with `admin` role, except where indicated.

| Method | Route | Description |
|---|---|---|
| GET, POST | `/api/admin/usuarios` | Lists or creates users |
| GET, PUT, PATCH, DELETE | `/api/admin/usuarios/<pk>` | Queries, edits, blocks or unblocks and deletes |
| GET | `/api/admin/stats` | System statistics |
| GET | `/api/admin/stats/stream` | Real-time statistics (SSE) |
| GET | `/api/admin/logs` | System logs |
| GET | `/api/admin/logs/stream` | Real-time logs (SSE, with heartbeat) |
| GET | `/api/admin/online` | Connected users |
| GET | `/api/admin/roles/usuarios` · `/api/admin/roles/historial` | Roles and their history |
| GET, POST, DELETE | `/api/admin/notificaciones` · `/api/admin/notificaciones/<id>` | Panel notifications |
| GET, POST | `/api/admin/chatbot-config` | Chatbot configuration |
| PUT, PATCH, DELETE | `/api/admin/chatbot-config/<pk>` | Edits or deletes a configuration |
| GET | `/api/admin/chatbot-config/palabras-detectadas` | Words detected by chatbot |
| GET | `/api/admin/chatbot-historial` | Chatbot history (`nivel`, `q`) |
| POST | `/api/admin/crear-columnas-diagnostico` | Maintenance utility |

## 10. Utilities and health / Utilidades y salud

| Method | Route | Access | Description |
|---|---|---|---|
| GET | `/health/` · `/healthz/` (also `/api/health/`, `/api/healthz/`) | Public | Service status |
| GET, POST | `/api/theme` | No DRF class | Theme preference |
| GET, POST | `/api/newsletter/subscribe` | No DRF class | Newsletter subscription |
| GET, POST | `/api/client-errors` | No DRF class | Browser error logging |
| GET, POST | `/api/config/pago/` | No DRF class | Payment link data (`PAGO_CUENTA_URL`, `PAGO_CUENTA_NOMBRE`) |
| POST | `/api/whatsapp/webhook/` | No DRF class | Incoming WhatsApp webhook (Twilio) |
| GET | `/media/qr_codes/<archivo>` | Public | Professional payment QR |

## 11. API security notes / Notas de seguridad de la API

- **Available appointments** endpoints (`/api/citas/disponibles` and `/api/citas/fechas-disponibles`) do not require authentication.
- Several utility routes (`config/pago`, `newsletter`, `client-errors`, `theme`, `whatsapp/webhook`) do not declare DRF permission classes; it is advisable to confirm that each one validates what is necessary on its own.
- No OpenAPI documentation is generated automatically. An option is to add `drf-spectacular` to expose it at `/api/docs/`.