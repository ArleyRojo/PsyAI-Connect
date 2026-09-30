# PsyAI Connect — REST API Reference

All endpoints are prefixed with `/api/`. Authentication is session-based (no JWT).

**Roles:**

| Role | Description |
|---|---|
| `paciente` | Patient |
| `profesional` | Healthcare professional |
| `admin` | Administrator |

---

## Authentication (`apps/authentication/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| POST | `/api/register` | No | Public | Register new user |
| POST | `/api/login` | No | Public | Login, creates session |
| POST | `/api/logout` | No | Public | Flush session |
| GET | `/api/session` | No | Public | Check session status |
| POST | `/api/forgot-password` | No | Public | Request password recovery email |
| POST | `/api/reset-password` | No | Public | Reset password with token |

---

## Scheduling (`apps/scheduling/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/api/citas` | Yes | paciente, profesional | List own appointments |
| POST | `/api/citas` | Yes | paciente, profesional | Create appointment |
| PATCH | `/api/citas/<id>` | Yes | profesional | Update appointment status |
| DELETE | `/api/citas/<id>` | Yes | paciente, profesional | Cancel appointment |
| GET | `/api/citas/disponibles` | No | Public | Available times for a professional |
| GET | `/api/citas/fechas-disponibles` | No | Public | Available dates for a month |
| GET | `/api/citas/proxima` | Yes | paciente | Next pending appointment |
| GET | `/api/citas/horarios-ocupados` | Yes | profesional | Booked times for professional |

---

## Billing (`apps/billing/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/api/facturas` | Yes | All | List invoices (filtered by role) |
| POST | `/api/facturas` | Yes | All | Create invoice |
| GET | `/api/facturas/<id>` | Yes | All | Get invoice detail |
| PATCH | `/api/facturas/<id>` | Yes | All | Annul or update invoice status |
| DELETE | `/api/facturas/<id>` | Yes | All | Annul invoice |
| POST | `/api/facturas/<id>/iniciar-pago` | Yes | paciente | Initiate Wompi payment |
| POST | `/api/facturas/<id>/confirmar-pago` | Yes | paciente | Confirm payment |
| DELETE | `/api/facturas/<id>/pago` | Yes | paciente | Cancel payment |
| GET | `/api/facturas/stats` | Yes | All | Invoice statistics |
| GET | `/api/facturas/pacientes-profesional` | Yes | profesional | List patients for professional |
| GET | `/api/facturas/estadisticas-admin` | Yes | admin | Global invoice KPIs |
| POST | `/api/webhooks/wompi` | No | Webhook | Wompi payment notification |

---

## Patients (`apps/patients/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/api/perfil/paciente/<id>` | Yes | All | Get patient profile |
| PUT | `/api/perfil/paciente` | Yes | paciente | Update own profile |
| PUT | `/api/perfil/paciente/foto` | Yes | All | Upload profile photo |
| GET | `/api/evolucion` | Yes | paciente | Evolution history |
| POST | `/api/evolucion` | Yes | paciente | Save evolution entry |
| GET | `/api/pacientes` | Yes | profesional, admin | List patients |
| GET | `/api/profesionales` | Yes | All | List professionals |
| GET | `/api/paciente/<id>/anamnesis` | Yes | profesional, admin | Get patient anamnesis |
| POST | `/api/paciente/<id>/anamnesis` | Yes | profesional, admin | Create patient anamnesis |
| PUT | `/api/paciente/<id>/anamnesis` | Yes | profesional, admin | Update patient anamnesis |
| DELETE | `/api/paciente/<id>/anamnesis` | Yes | profesional, admin | Delete patient anamnesis |

---

## Professionals (`apps/professionals/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/api/perfil/profesional/<id>` | Yes | admin, profesional, paciente | Get professional profile |
| PUT | `/api/perfil/profesional` | Yes | profesional | Update own profile |
| POST | `/api/disponibilidad` | Yes | profesional | Create availability slot |
| GET | `/api/disponibilidad/<id>` | Yes | admin, profesional, paciente | Get availability slot |
| GET | `/api/profesional/dashboard` | Yes | profesional | Dashboard data |
| GET | `/api/profesional/pacientes` | Yes | profesional | Patient list |
| GET | `/api/profesional/pacientes/todos` | Yes | profesional, admin | All patients (for assignment) |
| POST | `/api/profesional/pacientes/<id>/asignar` | Yes | profesional | Assign patient to professional |
| GET | `/api/diagnosticos` | Yes | profesional | List diagnoses |
| POST | `/api/diagnosticos` | Yes | profesional | Create diagnosis |
| GET | `/api/reportes` | Yes | profesional | List reports |
| POST | `/api/reportes` | Yes | profesional | Create report |
| PATCH | `/api/reportes/<id>` | Yes | profesional | Update report |
| DELETE | `/api/reportes/<id>` | Yes | profesional | Delete report |
| GET | `/api/evolucion/profesional` | Yes | profesional | All patient evolution entries |

---

## Documents (`apps/documents/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/api/documentos/profesional/<id_paciente>` | Yes | All | Professional docs for patient |
| POST | `/api/documentos/profesional/<id_paciente>` | Yes | All | Upload professional document |
| PATCH | `/api/documentos/profesional/doc/<id>` | Yes | All | Toggle document visibility |
| DELETE | `/api/documentos/profesional/doc/<id>` | Yes | All | Soft-delete professional document |
| GET | `/api/documentos/paciente/dashboard` | Yes | All | Patient document dashboard |
| GET | `/api/documentos/paciente` | Yes | paciente | List own documents |
| POST | `/api/documentos/paciente` | Yes | paciente | Upload own document |
| DELETE | `/api/documentos/paciente/doc/<id>` | Yes | paciente | Delete own document |
| POST | `/api/documentos/autorizacion/<id>` | Yes | paciente | Toggle professional access to document |

---

## Chatbot (`apps/chatbot/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| POST | `/api/chatbot` | Yes | paciente | Send message to chatbot |
| GET | `/api/chatbot` | Yes | paciente | Get chatbot history |
| DELETE | `/api/chatbot` | Yes | paciente | Delete chatbot history |
| GET | `/api/chatbot/config` | Yes | paciente | Get chatbot configuration |
| GET | `/api/chat/contactos` | Yes | paciente | List chat contacts |
| GET | `/api/chat/mensajes` | Yes | All | Get messages |
| POST | `/api/chat/mensajes` | Yes | All | Send message |
| DELETE | `/api/chat/historial` | Yes | paciente | Delete chat history |

---

## Admin (`apps/admin_panel/`)

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/api/admin/usuarios` | Yes | admin | List users |
| POST | `/api/admin/usuarios` | Yes | admin | Create user |
| PATCH | `/api/admin/usuarios/<id>` | Yes | admin | Block/unblock or change user role |
| DELETE | `/api/admin/notificaciones/<id>` | Yes | admin | Delete notification |
| GET | `/api/admin/stats` | Yes | admin | System statistics |
| GET | `/api/admin/logs` | Yes | admin | System logs (SSE stream) |
| GET | `/api/admin/usuarios-online` | Yes | admin | List online users |
| GET | `/api/admin/actividad` | Yes | admin | Recent activity feed |
