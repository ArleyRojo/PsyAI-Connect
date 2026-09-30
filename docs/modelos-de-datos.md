# Modelos de Datos — PsyAI Connect

> **Resumen:** Este documento describe el modelo de datos del proyecto: modelos principales por app, sus campos clave, relaciones (FK, OneToOne, M2M) y un diagrama entidad-relación en Mermaid.  
> **Audiencia:** Desarrolladores que necesitan entender la estructura de la base de datos sin leer todos los `models.py`.

---

## 1. `apps.authentication` — Usuario base y seguridad

### `Register` (tabla `Register`)
Usuario base del sistema. Hereda de `AbstractBaseUser`.

| Campo | Tipo | Detalle |
|-------|------|---------|
| `idUsuario` | `AutoField` | PK |
| `nombre` | `CharField(120)` | Nombre completo |
| `email` | `EmailField(unique)` | Username real (`USERNAME_FIELD`) |
| `contrasena` | `CharField(200)` | Hash bcrypt |
| `rol` | `CharField(20, choices)` | `paciente`, `profesional`, `admin` |
| `fotoPerfil` | `CharField(255, null)` | Ruta relativa del avatar |
| `estadoCuenta` | `CharField(20, choices)` | `Activa`, `Suspendida` |
| `activo` | `BooleanField` | Soft delete lógico |
| `email_verificado` | `BooleanField(default=False)` | Verificación de correo |
| `fechaRegistro` | `DateTimeField(auto_now_add)` | |

**Relaciones:**  
- 1→1 `PerfilPaciente` (related_name=`perfil_paciente`)  
- 1→1 `PerfilProfesional` (related_name=`perfil_profesional`)  
- 1→N `Login`, `RecoveryTokens`, `EmailVerificationToken`, `TOTPDevice`, `IntentosFallidos`  
- 1→N `Citas` (paciente/profesional), `Facturas`, `Documentos`, `ConversacionesChatbot`, `MensajesChat`, `Notificaciones`, `AuditoriaAccesos`

---

### `Login` (tabla `Login`)
Historial de accesos.

| Campo | Tipo |
|-------|------|
| `idLogin` | PK |
| `idUsuario` | FK → `Register` |
| `email` | CharField |
| `contrasena` | CharField (hash en el momento) |
| `ultimoAcceso` | DateTimeField |

---

### `RecoveryTokens` (tabla `RecoveryTokens`)
Tokens de recuperación de contraseña (1 hora, un solo uso).

| Campo | Tipo |
|-------|------|
| `id` | PK |
| `idUsuario` | FK → `Register` |
| `token` | CharField(100, unique) |
| `expires` | DateTimeField |
| `used` | BooleanField |
| `createdAt` | DateTimeField |

---

### `EmailVerificationToken` (tabla `EmailVerificationTokens`)
Verificación de email al registrarse (24 h, obligatorio para `profesional`).

| Campo | Tipo |
|-------|------|
| `id` | PK |
| `idUsuario` | FK → `Register` |
| `token` | CharField(100, unique) |
| `expires` | DateTimeField |
| `used` | BooleanField |
| `createdAt` | DateTimeField |

---

### `IntentosFallidos` (tabla `intentos_fallidos`)
Rate limiting y bloqueo por fuerza bruta.

| Campo | Tipo |
|-------|------|
| `id` | PK |
| `email` | CharField(255, unique) |
| `intentos` | IntegerField |
| `ultimo_intento` | DateTimeField |
| `bloqueado_hasta` | DateTimeField |

---

### `TOTPDevice` (tabla `TOTPDevices`)
Dispositivo TOTP para 2FA (RFC 6238). Opcional para `admin` y `profesional`.

| Campo | Tipo |
|-------|------|
| `id` | PK |
| `idUsuario` | OneToOne → `Register` (related_name=`totp_device`) |
| `secret` | CharField(64) — base32 |
| `name` | CharField(100) — nombre amigable |
| `confirmed` | BooleanField(default=False) |
| `createdAt` | DateTimeField |
| `last_used` | DateTimeField(null) |

---

## 2. `apps.patients` — Portal de pacientes

### `PerfilPaciente` (tabla `PerfilPaciente`)
Extensión 1→1 de `Register` para pacientes.

| Campo | Tipo |
|-------|------|
| `idPaciente` | OneToOne → `Register` (PK, related_name=`perfil_paciente`) |
| `genero` | CharField(20, null) |
| `edad` | IntegerField(null) |
| `numeroTelefonico` | CharField(20, null) |
| `consentimientoDatos` | BooleanField |
| `consentimiento_chatbot` | BooleanField |
| `prefNotificaciones` | CharField(choices: Activadas/Desactivadas) |
| `prefRecordatorios` | CharField(choices: Activados/Desactivados) |
| `prefContacto` | CharField(choices: Correo/WhatsApp/Teléfono) |

---

### `EvolucionPaciente` (tabla `EvolucionPaciente`)
Seguimiento diario del estado emocional.

| Campo | Tipo |
|-------|------|
| `idEvolucion` | PK |
| `idPaciente` | FK → `Register` (related_name=`evoluciones`) |
| `idConversacion` | IntegerField(null) — vincula a chatbot |
| `estadoEmocional` | CharField(100, null) |
| `nivelEnergia` | IntegerField(null) |
| `notasPersonales` | TextField(null) |
| `resultadoEmocional` | CharField(100, null) |
| `fecha` | DateTimeField(auto_now_add) |

---

### `Anamnesis` (tabla `Anamnesis`)
Historia clínica completa (anamnesis) registrada por un profesional para un paciente. **1→1** con `Register` (paciente).

| Campo | Tipo |
|-------|------|
| `idAnamnesis` | PK |
| `idPaciente` | OneToOne → `Register` (related_name=`anamnesis`) |
| `idProfesional` | FK → `Register` (related_name=`anamnesis_creadas`, null, SET_NULL) |
| `fechaActualizacion` | DateTimeField(auto_now) |

**Sección A — Personales**
| Campo | Tipo |
|-------|------|
| `tipoDocumento` | CharField(20, choices: CC/CE/TI/Pasaporte) |
| `numeroDocumento` | CharField(40) |
| `fechaNacimiento` | DateField |
| `edad` | IntegerField |
| `genero` | CharField(30) |
| `estadoCivil` | CharField(30) |
| `orientacionSexual` | CharField(30) |
| `razaEtnica` | CharField(40) |
| `lugarNacimiento` | CharField(120) |

**Sección B — Contacto**
| Campo | Tipo |
|-------|------|
| `telefonoPrincipal` | CharField(20) |
| `telefonoAlterno` | CharField(20) |
| `whatsapp` | CharField(20) |
| `correoAlterno` | EmailField(120) |
| `direccionResidencia` | CharField(200) |
| `ciudad` | CharField(80) |
| `departamento` | CharField(80) |
| `barrio` | CharField(80) |
| `codigoPostal` | CharField(10) |
| `emergenciaNombre` | CharField(120) |
| `emergenciaParentesco` | CharField(40) |
| `emergenciaTelefono` | CharField(20) |

**Sección C — Escolar**
| Campo | Tipo |
|-------|------|
| `nivelEscolar` | CharField(20, choices: ninguno/primaria/secundaria/tecnico/universitario/posgrado) |
| `institucionEducativa` | CharField(150) |
| `anoGraduacion` | IntegerField |
| `carreraEstudiada` | CharField(150) |
| `estudiaActualmente` | BooleanField |

**Sección D — Ocupación**
| Campo | Tipo |
|-------|------|
| `ocupacion` | CharField(120) |
| `situacionLaboral` | CharField(60) |
| `empresa` | CharField(150) |
| `cargo` | CharField(100) |
| `rangoIngresosMensuales` | CharField(20, choices: NO_INFORMA/SIN_INGRESOS/MENOS1SMM/1SMM2SMM/2SMM4SMM/4SMM6SMM/6SMM10SMM/MAS10SMM) |

**Sección E — Salud**
| Campo | Tipo |
|-------|------|
| `seguroSalud` | BooleanField |
| `epsNombre` | CharField(120) |
| `alergias` | TextField |
| `cirugiasPrevias` | TextField |
| `enfermedadesCronicas` | TextField |
| `medicamentosActuales` | TextField |
| `discapacidad` | BooleanField |
| `tipoDiscapacidad` | CharField(120) |

**Sección F — Psicosocial**
| Campo | Tipo |
|-------|------|
| `conviveCon` | CharField(80) |
| `personasQueVivenCon` | IntegerField |
| `cantidadHijos` | IntegerField |
| `consumoAlcohol` | CharField(40) |
| `consumoTabaco` | CharField(40) |
| `consumoSustancias` | TextField |
| `suenoHoras` | DecimalField(4,1) |
| `calidadSueno` | CharField(40) |
| `actividadFisica` | CharField(40) |

**Sección G/H — Entrevista**
| Campo | Tipo |
|-------|------|
| `motivoConsulta` | TextField |
| `antecedentesFamiliares` | TextField |
| `narrativa` | TextField |
| `observaciones` | TextField |
| `entrevistador` | CharField(120) |

**Propiedad:** `edad_calculada` (property) — calcula edad desde `fechaNacimiento`

---

### `Familiar` (tabla `AnamnesisFamiliar`)
Familiares registrados en la anamnesis. **N→1** con `Anamnesis` (related_name=`familiares`).

| Campo | Tipo |
|-------|------|
| `idFamiliar` | PK |
| `idAnamnesis` | FK → `Anamnesis` (CASCADE) |
| `tipoParentesco` | CharField(20, choices: PADRE/MADRE/HIJO/HIJA/ABUELO_PATERNO/ABUELA_PATERNA/ABUELO_MATERNO/ABUELA_MATERNA/BISABUELO/TIO/TIA/PRIMO/PRIMA/HERMANO/HERMANA/CONYUGE/OTRO) |
| `nombreCompleto` | CharField(120) |
| `fechaNacimiento` | DateField |
| `edad` | IntegerField |
| `sexo` | CharField(20) |
| `vivo` | BooleanField |
| `causaFallecimiento` | CharField(200) |
| `estadoSalud` | CharField(20, choices: sano/enfermedad_cronica/discapacidad/fallecido/desconocido) |
| `diagnosticoOEnfermedad` | TextField |
| `ocupacion` | CharField(120) |
| `telefono` | CharField(20) |
| `notas` | TextField |
| `orden` | IntegerField(default=0) |

---

## 3. `apps.professionals` — Portal de profesionales

### `PerfilProfesional` (tabla `PerfilProfesional`)
Extensión 1→1 de `Register` para profesionales.

| Campo | Tipo |
|-------|------|
| `idProfesional` | OneToOne → `Register` (PK, related_name=`perfil_profesional`) |
| `genero` | CharField(20, null) |
| `edad` | IntegerField(null) |
| `especialidad` | CharField(120, null) |
| `licencia` | CharField(120, null) |
| `experiencia` | TextField(null) |
| `estado` | CharField(choices: Activo/Inactivo, default=Activo) |

---

### `PacientesProfesional` (tabla `PacientesProfesional`)
Relación profesional-paciente (asignación). Los datos clínicos (diagnósticos) están en la tabla separada `Diagnostico`.

| Campo | Tipo |
|-------|------|
| `idRegistro` | PK |
| `idProfesional` | FK → `Register` (related_name=`pacientes_profesional`) |
| `idPaciente` | FK → `Register` (related_name=`pacientes_asignados`, null) |
| `fecha` | DateTimeField(auto_now_add) |

**Constraint:** `UniqueConstraint(idProfesional, idPaciente)` → `uq_profesional_paciente`

---

### `Diagnostico` (tabla `Diagnostico`)
Historial de diagnósticos por asignación profesional-paciente. **N→1** con `PacientesProfesional` (related_name=`diagnosticos`).

| Campo | Tipo |
|-------|------|
| `idDiagnostico` | PK |
| `idAsignacion` | FK → `PacientesProfesional` (CASCADE, related_name=`diagnosticos`) |
| `sintomas` | TextField |
| `diagnostico` | TextField |
| `tratamiento` | TextField |
| `fechaDiagnostico` | DateField |
| `fecha` | DateTimeField(auto_now_add) |

**Ordering:** `[-fechaDiagnostico, -fecha]`

---

### `Reportes` (tabla `Reportes`)
Reportes clínicos generados por el profesional.

| Campo | Tipo |
|-------|------|
| `idReporte` | PK |
| `idProfesional` | FK → `Register` (related_name=`reportes_profesional`) |
| `idPaciente` | FK → `Register` (related_name=`reportes_paciente`, null) |
| `tipoReporte` | CharField(80, null) |
| `fechaInicio` / `fechaFin` | DateField(null) |
| `estado` | CharField(default=Pendiente) |
| `eliminado` | BooleanField(default=False) |
| `sintomas`, `diagnostico`, `tratamiento` | TextField(null) |
| `fecha` | DateTimeField(auto_now_add) |

---

## 4. `apps.scheduling` — Agenda y citas

### `Disponibilidad` (tabla `Disponibilidad`)
Slots de tiempo del profesional.

| Campo | Tipo |
|-------|------|
| `idDisponibilidad` | PK |
| `idProfesional` | FK → `Register` |
| `fecha` | DateField |
| `hora_inicio` / `hora_fin` | TimeField |
| `estado` | CharField(choices: Disponible/Bloqueado/Ocupado) |

---

### `Citas` (tabla `Citas`)
Citas agendadas.

| Campo | Tipo |
|-------|------|
| `idCita` | PK |
| `idPaciente` | FK → `Register` (related_name=`citas_paciente`) |
| `idProfesional` | FK → `Register` (related_name=`citas_profesional`) |
| `fecha` | DateField |
| `hora` | TimeField |
| `tipoCita` / `tipoSesion` | CharField(80, null) |
| `motivo` / `notas` | TextField(null) |
| `estado` | CharField(choices: Pendiente/Confirmada/Completada/Cancelada) |
| `creado_por_profesional` | BooleanField |
| `motivoCancelacion` | TextField(null) |

**Constraint:** `UniqueConstraint(idProfesional, fecha, hora)` condicionado a `estado IN ('Pendiente','Confirmada')` → `uniq_cita_prof_fecha_hora_active`

---

### `Notificaciones` (tabla `Notificaciones`)
Sistema de notificaciones multi-rol.

| Campo | Tipo |
|-------|------|
| `idNotificacion` | PK |
| `idUsuario` | FK → `Register` (SET_NULL) |
| `rol` | CharField(choices: admin/profesional/paciente) |
| `titulo`, `mensaje` | CharField / TextField |
| `tipo`, `destinatario` | CharField |
| `estado` | CharField(choices: enviado/pendiente) |
| `leido` | BooleanField |
| `fecha_programada` | DateTimeField(null) |

---

## 5. `apps.billing` — Facturación

### `Facturas` (tabla `Facturas`)
Facturas con integración Wompi.

| Campo | Tipo |
|-------|------|
| `idFactura` | PK |
| `idPaciente` | FK → `Register` (related_name=`facturas_paciente`) |
| `idProfesional` | FK → `Register` (related_name=`facturas_profesional`) |
| `idCita` | IntegerField(null) |
| `monto` | DecimalField(10,2) |
| `metodoPago` | CharField(choices: banco/tarjeta/efectivo/transferencia/pse) |
| `estadoPago` | CharField(choices: Pendiente/Parcial/Pagado/Cancelado) |
| `anulada` | BooleanField |
| `referenciaPago` | CharField(64, null) — hash Wompi |
| `idTransaccionPago` | CharField(64, null) |

**Relación:** 1→N `ItemsFactura` (related_name=`items`)

---

### `ItemsFactura` (tabla `ItemsFactura`)
Líneas de factura.

| Campo | Tipo |
|-------|------|
| `idItem` | PK |
| `idFactura` | FK → `Facturas` (related_name=`items`) |
| `descripcion` | CharField(120, null) |
| `precioUnitario` | DecimalField(10,2) |

---

## 6. `apps.documents` — Documentos clínicos

### `DocumentosClinicos` (tabla `DocumentosClinicos`)
Documentos subidos por profesionales.

| Campo | Tipo |
|-------|------|
| `idDocumento` | PK |
| `idProfesional` | FK → `Register` (related_name=`documentos_clinicos`) |
| `idPaciente` | FK → `Register` (related_name=`documentos_paciente_prof`) |
| `nombreArchivo` | CharField(255) |
| `rutaArchivo` | CharField(500) |
| `tipoMime` | CharField(100, null) |
| `tamanoArchivo` | IntegerField |
| `categoria` | CharField(choices: Historia Clinica/Evolucion/Diagnostico/Consentimiento/Otro) |
| `visibilidad` | CharField(choices: privado/compartido) |
| `eliminado` | BooleanField |

---

### `DocumentosPaciente` (tabla `DocumentosPaciente`)
Documentos subidos por el propio paciente.

| Campo | Tipo |
|-------|------|
| `idDocumento` | PK |
| `idPaciente` | FK → `Register` (related_name=`documentos_paciente`) |
| `nombreArchivo`, `rutaArchivo`, `tipoMime`, `tamanoArchivo` | igual que arriba |
| `descripcion` | TextField(null) |
| `eliminado` | BooleanField |

---

### `AutorizacionesDocumento` (tabla `AutorizacionesDocumento`)
Control de acceso a documentos clínicos.

| Campo | Tipo |
|-------|------|
| `idAutorizacion` | PK |
| `idDocumento` | FK → `DocumentosClinicos` |
| `idProfesional` | FK → `Register` |
| `revocado` | BooleanField |
| `fechaRevocacion` | DateTimeField(null) |

**Constraint:** `unique_together = (idDocumento, idProfesional)`

---

## 7. `apps.chatbot` — Chatbot IA y chat directo

### `ConversacionesChatbot` (tabla `ConversacionesChatbot`)
Historial de interacciones paciente–chatbot.

| Campo | Tipo |
|-------|------|
| `idConversacion` | PK |
| `idPaciente` | FK → `Register` |
| `mensajeUsuario` / `respuestaChatbot` | TextField |
| `nivelEmocionalDetectado` | CharField(50, null) — alto/medio/bajo |
| `palabrasRiesgoDetectadas` | TextField(null) |
| `fecha` | DateTimeField |

---

### `EncuestaChatbot` (tabla `EncuestaChatbot`)
Feedback post-interacción.

| Campo | Tipo |
|-------|------|
| `id` | PK |
| `idPaciente` | FK → `Register` |
| `utilidad`, `claridad` | BooleanField |
| `recomendaria` | CharField(choices: si/no) |
| `comentario` | TextField(null) |

---

### `ChatbotConfig` (tabla `ChatbotConfig`)
Configuración del prompt y parámetros de Gemini (solo 1 fila activa).

| Campo | Tipo |
|-------|------|
| `system_prompt`, `tone`, `interaction_rules`, `risk_terms`, `crisis_response`, `medium_terms`, `medium_response`, `fallback_response`, `off_topic_response` | TextField |
| `crisis_phone` | CharField(default="106") |
| `thinking_level` | CharField(default=low) |
| `temperature`, `top_p` | FloatField |
| `max_tokens`, `max_tokens_user`, `daily_message_limit` | IntegerField |
| `actualizado_por` | FK → `Register` (SET_NULL) |

---

### `MensajesChat` (tabla `MensajesChat`)
Chat directo paciente–profesional (SSE).

| Campo | Tipo |
|-------|------|
| `idMensaje` | PK |
| `idEmisor` | FK → `Register` (related_name=`mensajes_enviados`) |
| `idReceptor` | FK → `Register` (related_name=`mensajes_recibidos`) |
| `mensaje` | TextField |
| `leido` | BooleanField |

---

### `PrediagnosticoChatbot` (tabla `PrediagnosticoChatbot`)
Prediagnóstico orientativo generado por IA al finalizar una sesión de chatbot. Se persiste para consulta del profesional.

| Campo | Tipo | Detalle |
|-------|------|---------|
| `idPrediagnostico` | `AutoField` | PK |
| `idPaciente` | FK → `Register` | Paciente de la sesión |
| `resumenPaciente` | `TextField` | Resumen cálido, en 2ª persona, para mostrar al paciente |
| `resumenProfesional` | `TextField` | Análisis técnico y objetivo con patrones observados |
| `posiblesAreas` | `JSONField(list)` | Áreas psicológicas detectadas (ej. `["Ansiedad", "Estrés"]`) |
| `recomendaciones` | `JSONField(list)` | Recomendaciones para el paciente |
| `nivelRiesgo` | `CharField(20, choices)` | `bajo` / `moderado` / `alto` / `critico` |
| `requiereAtencionUrgente` | `BooleanField` | `True` si el modelo o el historial detectan riesgo alto/crítico |
| `profesionalNotificado` | `BooleanField` | `True` tras enviar notificación al profesional |
| `fecha` | `DateTimeField(auto_now_add)` | Fecha de generación |

**Notas:**
- Si algún mensaje del historial del día tiene `nivelEmocionalDetectado` en `{alto, critico}`, el servicio fuerza `requiereAtencionUrgente=True` independientemente del modelo (ver `chatbot-ia.md §9.4`).
- `resumenPaciente` y `recomendaciones` son los únicos campos visibles al paciente (modal del chatbot). El `resumenProfesional` y `nivelRiesgo` solo se muestran en la vista del profesional.

---

## 8. `apps.core` — Utilidades transversales


### `NewsletterSubscriber` (tabla `NewsletterSubscribers`)
Suscriptores al boletín.

| Campo | Tipo |
|-------|------|
| `email` | EmailField(unique, db_index) |
| `is_active` | BooleanField |
| `created_at` | DateTimeField |

---

## 9. `apps.admin_panel` — Auditoría

### `AuditoriaAccesos` (tabla `AuditoriaAccesos`)
Log de accesos al sistema.

| Campo | Tipo |
|-------|------|
| `idAuditoria` | PK |
| `idUsuario` | FK → `Register` (related_name=`accesos`) |
| `accion` | CharField(100) |
| `ip` | CharField(50) |
| `fecha` | DateTimeField |

---

### `Logs` (tabla `Logs`)
Log de acciones administrativas.

| Campo | Tipo |
|-------|------|
| `idLog` | PK |
| `administrador`, `modulo`, `accion`, `detalle` | CharField / TextField |
| `rol_anterior`, `rol_nuevo` | CharField |
| `usuario_afectado` | CharField |

---

## Diagrama Entidad-Relación (Mermaid)

```mermaid
erDiagram
    Register ||--|| PerfilPaciente : "1:1"
    Register ||--|| PerfilProfesional : "1:1"
    Register ||--o{ Login : "1:N"
    Register ||--o{ RecoveryTokens : "1:N"
    Register ||--o{ EmailVerificationToken : "1:N"
    Register ||--o{ IntentosFallidos : "1:N"
    Register ||--o| TOTPDevice : "1:0..1"
    Register ||--o{ Citas : "paciente"
    Register ||--o{ Citas : "profesional"
    Register ||--o{ Facturas : "paciente"
    Register ||--o{ Facturas : "profesional"
    Register ||--o{ DocumentosClinicos : "profesional"
    Register ||--o{ DocumentosClinicos : "paciente"
    Register ||--o{ DocumentosPaciente : "paciente"
    Register ||--o{ ConversacionesChatbot : "1:N"
    Register ||--o{ MensajesChat : "emisor"
    Register ||--o{ MensajesChat : "receptor"
    Register ||--o{ Notificaciones : "1:N"
    Register ||--o{ AuditoriaAccesos : "1:N"
    Register ||--o{ PacientesProfesional : "profesional"
    Register ||--o{ PacientesProfesional : "paciente"
    Register ||--o{ Reportes : "profesional"
    Register ||--o{ Reportes : "paciente"
    Register ||--o{ Disponibilidad : "1:N"
    Register ||--o{ Notificaciones : "1:N"
    Register ||--o{ DocumentosClinicos : "profesional"
    Register ||--o{ DocumentosClinicos : "paciente"
    Register ||--o{ DocumentosPaciente : "1:N"
    Register ||--o{ ConversacionesChatbot : "1:N"
    Register ||--o{ EncuestaChatbot : "1:N"
    Register ||--o{ MensajesChat : "emisor"
    Register ||--o{ MensajesChat : "receptor"
    Register ||--o{ Notificaciones : "1:N"
    Register ||--o{ AuditoriaAccesos : "1:N"
    Register ||--o{ NewsletterSubscriber : "1:N"

    PerfilPaciente ||--|| Register : "1:1"
    PerfilProfesional ||--|| Register : "1:1"

    Register ||--o{ EvolucionPaciente : "1:N"
    Register ||--o{ PacientesProfesional : "profesional"
    Register ||--o{ PacientesProfesional : "paciente"
    Register ||--o{ Reportes : "profesional"
    Register ||--o{ Reportes : "paciente"
    Register ||--o{ Disponibilidad : "1:N"
    Register ||--o{ Citas : "paciente"
    Register ||--o{ Citas : "profesional"
    Register ||--o{ Notificaciones : "1:N"
    Register ||--o{ Facturas : "paciente"
    Register ||--o{ Facturas : "profesional"
    Register ||--o{ DocumentosClinicos : "profesional"
    Register ||--o{ DocumentosClinicos : "paciente"
    Register ||--o{ DocumentosPaciente : "1:N"
    Register ||--o{ ConversacionesChatbot : "1:N"
    Register ||--o{ EncuestaChatbot : "1:N"
    Register ||--o{ MensajesChat : "emisor"
    Register ||--o{ MensajesChat : "receptor"
    Register ||--o{ Notificaciones : "1:N"
    Register ||--o{ AuditoriaAccesos : "1:N"
    Register ||--|| Anamnesis : "1:1 (paciente)"
    Register ||--o{ Anamnesis : "1:N (profesional)"
    Anamnesis ||--o{ Familiar : "1:N"
    PacientesProfesional ||--o{ Diagnostico : "1:N"

    Register }|--|| PerfilPaciente : "1:1"
    Register }|--|| PerfilProfesional : "1:1"
    Register }|--o| TOTPDevice : "1:0..1"
    Register }|--o{ RecoveryTokens : "1:N"
    Register }|--o{ EmailVerificationToken : "1:N"
    Register }|--o{ IntentosFallidos : "1:N"

    Facturas ||--o{ ItemsFactura : "1:N"
    DocumentosClinicos ||--o| AutorizacionesDocumento : "1:0..N"
    Citas }|--|| Disponibilidad : "N:1 (slot)"
    PacientesProfesional }|--|| Register : "profesional"
    PacientesProfesional }|--|| Register : "paciente"
    Reportes }|--|| Register : "profesional"
    Reportes }|--|| Register : "paciente"
    Citas }|--|| Register : "paciente"
    Citas }|--|| Register : "profesional"
    Disponibilidad }|--|| Register : "profesional"
    Notificaciones }|--o| Register : "usuario"
    DocumentosClinicos }|--|| Register : "profesional"
    DocumentosClinicos }|--|| Register : "paciente"
    DocumentosPaciente }|--|| Register : "paciente"
    AutorizacionesDocumento }|--|| DocumentosClinicos : "documento"
    AutorizacionesDocumento }|--|| Register : "profesional"
    ConversacionesChatbot }|--|| Register : "paciente"
    EncuestaChatbot }|--|| Register : "paciente"
    ChatbotConfig }|--o| Register : "actualizado_por"
    MensajesChat }|--|| Register : "emisor"
    MensajesChat }|--|| Register : "receptor"
    PrediagnosticoChatbot }|--|| Register : "paciente"
    Notificaciones }|--o| Register : "usuario"
    AuditoriaAccesos }|--|| Register : "usuario"
    Logs }|--o| Register : "administrador"

    Citas }|..| Disponibilidad : "ocupa slot"
    Facturas }|..| Citas : "vinculada a cita (opcional)"
    ItemsFactura }|--|| Facturas : "líneas"
    DocumentosClinicos }|..| AutorizacionesDocumento : "control acceso"
    ConversacionesChatbot }|..| EvolucionPaciente : "idConversacion"
```

---

## Ver también

- [`roles-y-permisos.md`](roles-y-permisos.md) — Qué modelos ve cada rol
- [`frontend.md`](frontend.md) — Cómo se consumen estos modelos desde el frontend
- [`chatbot-ia.md`](chatbot-ia.md) — Modelos específicos del chatbot
- [`pagos-facturacion.md`](pagos-facturacion.md) — Modelos de facturación
- [`seguridad.md`](seguridad.md) — Modelos de seguridad (`TOTPDevice`, `RecoveryTokens`, etc.)