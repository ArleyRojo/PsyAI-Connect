import logging
from app.database.connection import get_connection

logger = logging.getLogger(__name__)

def init_db():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        create_statements = [
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
            """
            CREATE TABLE IF NOT EXISTS PerfilPaciente (
                idPaciente INT PRIMARY KEY,
                genero VARCHAR(20),
                edad INT,
                numeroTelefonico VARCHAR(20),
                FOREIGN KEY (idPaciente) REFERENCES Register(idUsuario) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
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
            """
            CREATE TABLE IF NOT EXISTS Login (
                idLogin INT AUTO_INCREMENT PRIMARY KEY,
                idUsuario INT NOT NULL,
                email VARCHAR(100) NOT NULL,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (idUsuario) REFERENCES Register(idUsuario) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
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
                actualizado_por INT,
                fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (actualizado_por) REFERENCES Register(idUsuario) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
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
        ]

        for stmt in create_statements:
            cursor.execute(stmt)

        # Columnas adicionales para tablas existentes
        extra_alters = []
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'Logs' AND COLUMN_NAME = 'rol_anterior' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE Logs ADD COLUMN rol_anterior VARCHAR(20) DEFAULT NULL")
        
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'Logs' AND COLUMN_NAME = 'rol_nuevo' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE Logs ADD COLUMN rol_nuevo VARCHAR(20) DEFAULT NULL")
        
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'Logs' AND COLUMN_NAME = 'usuario_afectado' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE Logs ADD COLUMN usuario_afectado VARCHAR(100) DEFAULT NULL")
        
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'Reportes' AND COLUMN_NAME = 'eliminado' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE Reportes ADD COLUMN eliminado TINYINT(1) DEFAULT 0")

        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'Citas' AND COLUMN_NAME = 'motivoCancelacion' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE Citas ADD COLUMN motivoCancelacion TEXT DEFAULT NULL")

        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'PerfilPaciente' AND COLUMN_NAME = 'consentimiento_chatbot' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE PerfilPaciente ADD COLUMN consentimiento_chatbot TINYINT(1) DEFAULT 0")

        for column_name, alter in (
            ("tone", "ALTER TABLE ChatbotConfig ADD COLUMN tone VARCHAR(120) DEFAULT NULL"),
            ("interaction_rules", "ALTER TABLE ChatbotConfig ADD COLUMN interaction_rules TEXT DEFAULT NULL"),
            ("medium_terms", "ALTER TABLE ChatbotConfig ADD COLUMN medium_terms TEXT DEFAULT NULL"),
            ("medium_response", "ALTER TABLE ChatbotConfig ADD COLUMN medium_response TEXT DEFAULT NULL"),
        ):
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_NAME = 'ChatbotConfig' AND COLUMN_NAME = %s AND TABLE_SCHEMA = DATABASE()
            """, (column_name,))
            if cursor.fetchone()[0] == 0:
                extra_alters.append(alter)

        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'Citas' AND COLUMN_NAME = 'creado_por_profesional' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE Citas ADD COLUMN creado_por_profesional BOOLEAN DEFAULT FALSE")

        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = 'rol' AND TABLE_SCHEMA = DATABASE()
        """)
        if cursor.fetchone()[0] == 0:
            extra_alters.append("ALTER TABLE Notificaciones ADD COLUMN rol ENUM('admin','profesional','paciente') DEFAULT NULL")

        cursor.execute("""
            SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS
            WHERE TABLE_NAME = 'Register' AND COLUMN_NAME = 'fotoPerfil' AND TABLE_SCHEMA = DATABASE()
        """)
        foto_col = cursor.fetchone()
        if foto_col and foto_col[0] and int(foto_col[0]) < 255:
            extra_alters.append("ALTER TABLE Register MODIFY COLUMN fotoPerfil VARCHAR(255) DEFAULT NULL")

        for column_name, alter in (
            ("destinatario", "ALTER TABLE Notificaciones ADD COLUMN destinatario VARCHAR(80) DEFAULT NULL"),
            ("email_individual", "ALTER TABLE Notificaciones ADD COLUMN email_individual VARCHAR(120) DEFAULT NULL"),
            ("leido", "ALTER TABLE Notificaciones ADD COLUMN leido TINYINT(1) DEFAULT 0"),
            ("fecha_programada", "ALTER TABLE Notificaciones ADD COLUMN fecha_programada DATETIME DEFAULT NULL"),
        ):
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = %s AND TABLE_SCHEMA = DATABASE()
            """, (column_name,))
            if cursor.fetchone()[0] == 0:
                extra_alters.append(alter)

        cursor.execute("""
            SELECT IS_NULLABLE FROM information_schema.COLUMNS
            WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = 'idUsuario' AND TABLE_SCHEMA = DATABASE()
        """)
        id_usuario_col = cursor.fetchone()
        if id_usuario_col and id_usuario_col[0] == "NO":
            extra_alters.append("ALTER TABLE Notificaciones MODIFY COLUMN idUsuario INT DEFAULT NULL")

        cursor.execute("""
            SELECT COLUMN_TYPE FROM information_schema.COLUMNS
            WHERE TABLE_NAME = 'Notificaciones' AND COLUMN_NAME = 'estado' AND TABLE_SCHEMA = DATABASE()
        """)
        estado_col = cursor.fetchone()
        if estado_col and "pendiente" not in estado_col[0]:
            extra_alters.append("ALTER TABLE Notificaciones MODIFY COLUMN estado ENUM('enviado','pendiente') DEFAULT 'enviado'")

        for alter in extra_alters:
            cursor.execute(alter)

        conn.commit()
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error(f"Error inicializando DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
