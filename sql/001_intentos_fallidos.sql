CREATE TABLE IF NOT EXISTS intentos_fallidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    intentos INT NOT NULL DEFAULT 0,
    ultimo_intento DATETIME NULL,
    bloqueado_hasta DATETIME NULL,
    UNIQUE KEY uk_email (email)
);
