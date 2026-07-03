# ============================================================
# ARCHIVO: database/migrations.py
# ============================================================

import logging
from sqlalchemy import text
from app.database.session import db_session

logger = logging.getLogger(__name__)


class MigrationRunner:
    def run(self):
        try:
            with db_session() as session:

                # Lista de CREATE TABLE que definen todo el esquema de la base de datos
                create_statements = [
                    # Tabla principal de usuarios — unifica pacientes, profesionales y admins
                    """
                    CREATE TABLE IF NOT EXISTS Register (
                        idUsuario INT AUTO_INCREMENT PRIMARY KEY,
                        nombre VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        contrasena VARCHAR(255) NOT NULL,
                        rol ENUM('admin','paciente','profesional') DEFAULT 'paciente',
                        activo TINYINT(1) DEFAULT 1,
                        estadoCuenta ENUM('Activa','Suspendida') DEFAULT 'Activa',
                        fechaRegistro DATETIME DEFAULT CURRENT_TIMESTAMP,
                        fotoPerfil VARCHAR(255) DEFAULT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Perfil específico del paciente con datos demográficos básicos
                    """
                    CREATE TABLE IF NOT EXISTS PerfilPaciente (
                        idPaciente INT PRIMARY KEY,
                        genero VARCHAR(20),
                        edad INT,
                        numeroTelefonico VARCHAR(20),
                        FOREIGN KEY (idPaciente) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Perfil del profesional con datos de especialidad y licencia
                    """
                    CREATE TABLE IF NOT EXISTS PerfilProfesional (
                        idProfesional INT PRIMARY KEY,
                        especialidad VARCHAR(100),
                        licencia VARCHAR(100),
                        experiencia INT,
                        estado VARCHAR(20) DEFAULT 'Activo',
                        FOREIGN KEY (idProfesional) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Auditoría de accesos: registra cada login de los usuarios para trazabilidad
                    """
                    CREATE TABLE IF NOT EXISTS AuditoriaAccesos (
                        idAuditoria INT AUTO_INCREMENT PRIMARY KEY,
                        idUsuario INT NOT NULL,
                        accion VARCHAR(50) NOT NULL,
                        ip VARCHAR(45) NOT NULL,
                        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (idUsuario) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Historial de logins: guarda cada inicio de sesión exitoso
                    """
                    CREATE TABLE IF NOT EXISTS Login (
                        idLogin INT AUTO_INCREMENT PRIMARY KEY,
                        idUsuario INT NOT NULL,
                        email VARCHAR(100) NOT NULL,
                        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (idUsuario) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Disponibilidad del profesional: slots de tiempo donde acepta citas
                    """
                    CREATE TABLE IF NOT EXISTS Disponibilidad (
                        idDisponibilidad INT AUTO_INCREMENT PRIMARY KEY,
                        idProfesional INT NOT NULL,
                        fecha DATE NOT NULL,
                        hora_inicio TIME NOT NULL,
                        hora_fin TIME NOT NULL,
                        estado ENUM('Disponible','Ocupado') DEFAULT 'Disponible',
                        FOREIGN KEY (idProfesional) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Citas médicas: asocian paciente-profesional con fecha, hora y estado
                    """
                    CREATE TABLE IF NOT EXISTS Citas (
                        idCita INT AUTO_INCREMENT PRIMARY KEY,
                        idPaciente INT NOT NULL,
                        idProfesional INT NOT NULL,
                        fecha DATE NOT NULL,
                        hora TIME NOT NULL,
                        tipoCita VARCHAR(100) NOT NULL,
                        motivo TEXT,
                        estado ENUM('Pendiente','Completada','Cancelada') DEFAULT 'Pendiente',
                        creado_por_profesional BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (idPaciente) REFERENCES Register(idUsuario) ON DELETE CASCADE,
                        FOREIGN KEY (idProfesional) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Conversaciones del chatbot de triaje emocional
                    """
                    CREATE TABLE IF NOT EXISTS ConversacionesChatbot (
                        idConversacion INT AUTO_INCREMENT PRIMARY KEY,
                        idPaciente INT NOT NULL,
                        mensajeUsuario TEXT,
                        respuestaChatbot TEXT,
                        nivelEmocionalDetectado VARCHAR(50),
                        palabrasRiesgoDetectadas TEXT,
                        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (idPaciente) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Evolución del paciente: registro diario de estado emocional y energía
                    """
                    CREATE TABLE IF NOT EXISTS EvolucionPaciente (
                        idEvolucion INT AUTO_INCREMENT PRIMARY KEY,
                        idPaciente INT NOT NULL,
                        estadoEmocional VARCHAR(100),
                        nivelEnergia INT,
                        notasPersonales TEXT,
                        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (idPaciente) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Relación paciente-profesional con datos de diagnóstico y tratamiento
                    """
                    CREATE TABLE IF NOT EXISTS PacientesProfesional (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        idProfesional INT NOT NULL,
                        idPaciente INT NOT NULL,
                        sintomas TEXT,
                        diagnostico TEXT,
                        tratamiento TEXT,
                        fechaDiagnostico DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (idProfesional) REFERENCES Register(idUsuario) ON DELETE CASCADE,
                        FOREIGN KEY (idPaciente) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Notificaciones del sistema (alertas de citas, recordatorios, eventos de seguridad)
                    """
                    CREATE TABLE IF NOT EXISTS Notificaciones (
                        idNotificacion INT AUTO_INCREMENT PRIMARY KEY,
                        idUsuario INT DEFAULT NULL,
                        rol ENUM('admin','profesional','paciente') DEFAULT NULL,
                        titulo VARCHAR(200) DEFAULT NULL,
                        mensaje TEXT DEFAULT NULL,
                        tipo VARCHAR(50) DEFAULT 'Cita',
                        destinatario VARCHAR(80) DEFAULT NULL,
                        email_individual VARCHAR(120) DEFAULT NULL,
                        enviado_por VARCHAR(120) DEFAULT 'Sistema',
                        estado ENUM('enviado','pendiente') DEFAULT 'enviado',
                        leido TINYINT(1) DEFAULT 0,
                        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                        fecha_programada DATETIME DEFAULT NULL,
                        FOREIGN KEY (idUsuario) REFERENCES Register(idUsuario) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Configuración dinámica del chatbot (prompts, límites, reglas de interacción)
                    """
                    CREATE TABLE IF NOT EXISTS ChatbotConfig (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        system_prompt TEXT,
                        tone VARCHAR(50) DEFAULT NULL,
                        interaction_rules TEXT,
                        welcome_message TEXT,
                        closing_message TEXT,
                        empathetic_message TEXT,
                        risk_terms TEXT,
                        crisis_response TEXT,
                        fallback_response TEXT,
                        temperature FLOAT DEFAULT 0.55,
                        top_p FLOAT DEFAULT 0.9,
                        max_tokens INT DEFAULT 420,
                        daily_message_limit INT DEFAULT 20,
                        actualizado_por INT,
                        fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (actualizado_por) REFERENCES Register(idUsuario) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Encuesta de satisfacción del chatbot respondida por pacientes
                    """
                    CREATE TABLE IF NOT EXISTS EncuestaChatbot (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        idPaciente INT NOT NULL,
                        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                        utilidad TINYINT(1) NOT NULL,
                        claridad TINYINT(1) NOT NULL,
                        recomendaria ENUM('si','no') NOT NULL,
                        comentario TEXT,
                        FOREIGN KEY (idPaciente) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Mensajería directa entre pacientes y profesionales
                    """
                    CREATE TABLE IF NOT EXISTS MensajesChat (
                        idMensaje   INT AUTO_INCREMENT PRIMARY KEY,
                        idEmisor    INT NOT NULL,
                        idReceptor  INT NOT NULL,
                        mensaje     TEXT NOT NULL,
                        leido       TINYINT(1) DEFAULT 0,
                        fecha       DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (idEmisor)   REFERENCES Register(idUsuario) ON DELETE CASCADE,
                        FOREIGN KEY (idReceptor) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Tokens para recuperación de contraseña (expiran y se marcan como usados)
                    """
                    CREATE TABLE IF NOT EXISTS RecoveryTokens (
                        id        INT AUTO_INCREMENT PRIMARY KEY,
                        idUsuario INT NOT NULL,
                        token     VARCHAR(100) NOT NULL UNIQUE,
                        expires   DATETIME NOT NULL,
                        used      TINYINT(1) DEFAULT 0,
                        createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (idUsuario) REFERENCES Register(idUsuario) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Control de intentos fallidos de login para protección contra brute-force
                    """
                    CREATE TABLE IF NOT EXISTS intentos_fallidos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        email VARCHAR(255) NOT NULL,
                        intentos INT NOT NULL DEFAULT 0,
                        ultimo_intento DATETIME NULL,
                        bloqueado_hasta DATETIME NULL,
                        UNIQUE KEY uk_email (email)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    # Vista que combina datos del chatbot con nombres de pacientes para el panel admin
                    """
                    CREATE OR REPLACE VIEW vistahistorialchatbot AS
                    SELECT
                        r.nombre,
                        r.idUsuario AS idPaciente,
                        c.mensajeUsuario,
                        c.respuestaChatbot,
                        c.nivelEmocionalDetectado,
                        c.palabrasRiesgoDetectadas,
                        c.fecha
                    FROM ConversacionesChatbot c
                    INNER JOIN Register r ON c.idPaciente = r.idUsuario
                    """,
                ]

                # Desactiva temporalmente la verificación de claves foráneas para evitar errores de orden
                session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                for stmt in create_statements:
                    try:
                        session.execute(stmt)
                    except Exception as e:
                        logger.warning(f"Error creando tabla: {e}")
                session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

                # Migraciones adicionales: agrega columnas faltantes a tablas existentes
                extra_alters = []
                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'Logs' AND COLUMN_NAME = 'rol_anterior' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE Logs ADD COLUMN rol_anterior VARCHAR(20) DEFAULT NULL")
                
                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'Logs' AND COLUMN_NAME = 'rol_nuevo' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE Logs ADD COLUMN rol_nuevo VARCHAR(20) DEFAULT NULL")
                
                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'Logs' AND COLUMN_NAME = 'usuario_afectado' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE Logs ADD COLUMN usuario_afectado VARCHAR(100) DEFAULT NULL")
                
                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'Reportes' AND COLUMN_NAME = 'eliminado' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE Reportes ADD COLUMN eliminado TINYINT(1) DEFAULT 0")

                for column_name in ("sintomas", "diagnostico", "tratamiento"):
                    if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                            WHERE TABLE_NAME = 'Reportes' AND COLUMN_NAME = :val AND TABLE_SCHEMA = DATABASE()"""), {"val": column_name}).scalar() == 0:
                        extra_alters.append(f"ALTER TABLE Reportes ADD COLUMN {column_name} TEXT DEFAULT NULL")

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'Citas' AND COLUMN_NAME = 'motivoCancelacion' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE Citas ADD COLUMN motivoCancelacion TEXT DEFAULT NULL")

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'PerfilPaciente' AND COLUMN_NAME = 'consentimiento_chatbot' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE PerfilPaciente ADD COLUMN consentimiento_chatbot TINYINT(1) DEFAULT 0")

                for column_name, alter in (
                    ("tone", "ALTER TABLE ChatbotConfig ADD COLUMN tone VARCHAR(120) DEFAULT NULL"),
                    ("interaction_rules", "ALTER TABLE ChatbotConfig ADD COLUMN interaction_rules TEXT DEFAULT NULL"),
                    ("medium_terms", "ALTER TABLE ChatbotConfig ADD COLUMN medium_terms TEXT DEFAULT NULL"),
                    ("medium_response", "ALTER TABLE ChatbotConfig ADD COLUMN medium_response TEXT DEFAULT NULL"),
                    ("daily_message_limit", "ALTER TABLE ChatbotConfig ADD COLUMN daily_message_limit INT DEFAULT 20"),
                    ("max_tokens_user", "ALTER TABLE ChatbotConfig ADD COLUMN max_tokens_user INT DEFAULT 2000"),
                ):
                    if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS
                            WHERE TABLE_NAME = 'ChatbotConfig' AND COLUMN_NAME = :val AND TABLE_SCHEMA = DATABASE()"""), {"val": column_name}).scalar() == 0:
                        extra_alters.append(alter)

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'Citas' AND COLUMN_NAME = 'creado_por_profesional' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE Citas ADD COLUMN creado_por_profesional BOOLEAN DEFAULT FALSE")

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = 'rol' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE Notificaciones ADD COLUMN rol ENUM('admin','profesional','paciente') DEFAULT NULL")

                foto_col = session.execute(text("""SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = 'Register' AND COLUMN_NAME = 'fotoPerfil' AND TABLE_SCHEMA = DATABASE()""")).scalar()
                if foto_col and int(foto_col) < 255:
                    extra_alters.append("ALTER TABLE Register MODIFY COLUMN fotoPerfil VARCHAR(255) DEFAULT NULL")

                for column_name, alter in (
                    ("destinatario", "ALTER TABLE Notificaciones ADD COLUMN destinatario VARCHAR(80) DEFAULT NULL"),
                    ("email_individual", "ALTER TABLE Notificaciones ADD COLUMN email_individual VARCHAR(120) DEFAULT NULL"),
                    ("leido", "ALTER TABLE Notificaciones ADD COLUMN leido TINYINT(1) DEFAULT 0"),
                    ("fecha_programada", "ALTER TABLE Notificaciones ADD COLUMN fecha_programada DATETIME DEFAULT NULL"),
                ):
                    if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS
                            WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = :val AND TABLE_SCHEMA = DATABASE()"""), {"val": column_name}).scalar() == 0:
                        extra_alters.append(alter)

                id_usuario_col = session.execute(text("""SELECT IS_NULLABLE FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = 'idUsuario' AND TABLE_SCHEMA = DATABASE()""")).scalar()
                if id_usuario_col and id_usuario_col == "NO":
                    extra_alters.append("ALTER TABLE Notificaciones MODIFY COLUMN idUsuario INT DEFAULT NULL")

                estado_col = session.execute(text("""SELECT COLUMN_TYPE FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = 'estado' AND TABLE_SCHEMA = DATABASE()""")).scalar()
                if estado_col and "pendiente" not in estado_col:
                    extra_alters.append("ALTER TABLE Notificaciones MODIFY COLUMN estado ENUM('enviado','pendiente') DEFAULT 'enviado'")

                estado_pago_col = session.execute(text("""SELECT COLUMN_TYPE FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = 'facturas' AND COLUMN_NAME = 'estadoPago' AND TABLE_SCHEMA = DATABASE()""")).scalar()
                if estado_pago_col and "Cancelado" not in estado_pago_col:
                    extra_alters.append("ALTER TABLE facturas MODIFY COLUMN estadoPago ENUM('Pendiente','Parcial','Pagado','Cancelado') DEFAULT 'Pendiente'")

                metodo_pago_col = session.execute(text("""SELECT COLUMN_TYPE FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = 'facturas' AND COLUMN_NAME = 'metodoPago' AND TABLE_SCHEMA = DATABASE()""")).scalar()
                if metodo_pago_col and "pse" not in metodo_pago_col:
                    extra_alters.append("ALTER TABLE facturas MODIFY COLUMN metodoPago ENUM('banco','tarjeta','efectivo','transferencia','pse') DEFAULT 'tarjeta'")

                for column_name, alter in (
                    ("anulada", "ALTER TABLE facturas ADD COLUMN anulada BOOLEAN DEFAULT FALSE"),
                    ("motivoAnulacion", "ALTER TABLE facturas ADD COLUMN motivoAnulacion VARCHAR(255) DEFAULT NULL"),
                    ("referenciaPago", "ALTER TABLE facturas ADD COLUMN referenciaPago VARCHAR(64) DEFAULT NULL"),
                    ("idTransaccionPago", "ALTER TABLE facturas ADD COLUMN idTransaccionPago VARCHAR(64) DEFAULT NULL"),
                ):
                    if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS
                            WHERE TABLE_NAME = 'facturas' AND COLUMN_NAME = :val AND TABLE_SCHEMA = DATABASE()"""), {"val": column_name}).scalar() == 0:
                        extra_alters.append(alter)

                for old_col, new_col in (("wompiReference", "referenciaPago"), ("wompiTransactionId", "idTransaccionPago")):
                    if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS
                            WHERE TABLE_NAME = 'facturas' AND COLUMN_NAME = :val AND TABLE_SCHEMA = DATABASE()"""), {"val": old_col}).scalar() == 1:
                        if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS
                                WHERE TABLE_NAME = 'facturas' AND COLUMN_NAME = :val AND TABLE_SCHEMA = DATABASE()"""), {"val": new_col}).scalar() == 0:
                            extra_alters.append(f"ALTER TABLE facturas RENAME COLUMN {old_col} TO {new_col}")

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = 'PacientesProfesional' AND COLUMN_NAME = 'diagnostico' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE PacientesProfesional ADD COLUMN diagnostico TEXT DEFAULT NULL")

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'PacientesProfesional' AND COLUMN_NAME = 'tratamiento' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE PacientesProfesional ADD COLUMN tratamiento TEXT DEFAULT NULL")

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'PacientesProfesional' AND COLUMN_NAME = 'fechaDiagnostico' AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE PacientesProfesional ADD COLUMN fechaDiagnostico DATETIME DEFAULT CURRENT_TIMESTAMP")

                if session.execute(text("""SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_NAME = 'PacientesProfesional' 
                      AND CONSTRAINT_NAME = 'uq_profesional_paciente' 
                      AND TABLE_SCHEMA = DATABASE()""")).scalar() == 0:
                    extra_alters.append("ALTER TABLE PacientesProfesional ADD CONSTRAINT uq_profesional_paciente UNIQUE (idProfesional, idPaciente)")

                for column_name, alter in (
                    ("genero", "ALTER TABLE PerfilProfesional ADD COLUMN genero VARCHAR(20) DEFAULT NULL"),
                    ("edad", "ALTER TABLE PerfilProfesional ADD COLUMN edad INT DEFAULT NULL"),
                ):
                    if session.execute(text("""SELECT COUNT(*) FROM information_schema.COLUMNS
                            WHERE TABLE_NAME = 'PerfilProfesional' AND COLUMN_NAME = :val AND TABLE_SCHEMA = DATABASE()"""), {"val": column_name}).scalar() == 0:
                        extra_alters.append(alter)

                # Ejecuta cada ALTER TABLE individualmente, ignorando errores de columnas ya existentes
                for alter in extra_alters:
                    try:
                        session.execute(text(alter))
                    except Exception as e:
                        logger.warning(f"Saltando ALTER TABLE (columna opcional): {e}")

                logger.info("Base de datos inicializada correctamente")
        except Exception as e:
            logger.error(f"Error inicializando DB: {e}")
            raise
