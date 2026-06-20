-- =====================================================
-- Migration: 001_intentos_fallidos
-- Fecha:     2026-06-16
-- Descripcion: Tabla para control de intentos fallidos
--              de login y bloqueo por fuerza bruta.
-- =====================================================

CREATE TABLE IF NOT EXISTS intentos_fallidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    intentos INT NOT NULL DEFAULT 0,
    ultimo_intento DATETIME NULL,
    bloqueado_hasta DATETIME NULL,
    UNIQUE KEY uk_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
