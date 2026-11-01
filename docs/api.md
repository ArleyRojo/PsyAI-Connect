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