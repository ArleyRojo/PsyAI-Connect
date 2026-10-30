-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 26-10-2026
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `psyai_connect`
--

CREATE DATABASE IF NOT EXISTS `psyai_connect` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `psyai_connect`;

-- --------------------------------------------------------
-- PROCEDIMIENTOS ALMACENADOS
-- --------------------------------------------------------

DELIMITER $$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_AgendarCita` (
    IN `p_paciente` INT, 
    IN `p_profesional` INT, 
    IN `p_fecha` DATE, 
    IN `p_hora` TIME, 
    IN `p_tipoCita` VARCHAR(80), 
    IN `p_tipoSesion` VARCHAR(80), 
    IN `p_motivo` TEXT, 
    IN `p_notas` TEXT
)
BEGIN
    INSERT INTO `citas` (idPaciente, idProfesional, fecha, hora, tipoCita, tipoSesion, motivo, notas)
    VALUES (p_paciente, p_profesional, p_fecha, p_hora, p_tipoCita, p_tipoSesion, p_motivo, p_notas);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_CrearFactura` (
    IN `p_paciente` INT, 
    IN `p_profesional` INT, 
    IN `p_cita` INT, 
    IN `p_monto` DECIMAL(10,2), 
    IN `p_metodoPago` VARCHAR(20)
)
BEGIN
    INSERT INTO `facturas` (idPaciente, idProfesional, idCita, monto, metodoPago)
    VALUES (p_paciente, p_profesional, p_cita, p_monto, p_metodoPago);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_GenerarReporte` (
    IN `p_profesional` INT, 
    IN `p_paciente` INT, 
    IN `p_tipo` VARCHAR(80), 
    IN `p_fechaInicio` DATE, 
    IN `p_fechaFin` DATE
)
BEGIN
    INSERT INTO `reportes` (idProfesional, idPaciente, tipoReporte, fechaInicio, fechaFin)
    VALUES (p_profesional, p_paciente, p_tipo, p_fechaInicio, p_fechaFin);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_Login` (
    IN `p_email` VARCHAR(120), 
    IN `p_contra` VARCHAR(200)
)
BEGIN
    SELECT idUsuario, nombre, email, rol, estadoCuenta
    FROM `register`
    WHERE email = p_email
      AND contrasena = p_contra
      AND estadoCuenta = 'Activa';
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_Register` (
    IN `p_nombre` VARCHAR(120), 
    IN `p_email` VARCHAR(120), 
    IN `p_contra` VARCHAR(200), 
    IN `p_rol` VARCHAR(20)
)
BEGIN
    INSERT INTO `register` (nombre, email, contrasena, rol)
    VALUES (p_nombre, p_email, p_contra, p_rol);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_RegistrarEvolucion` (
    IN `p_paciente` INT, 
    IN `p_estadoEmocional` VARCHAR(100), 
    IN `p_nivelEnergia` INT, 
    IN `p_notas` TEXT
)
BEGIN
    INSERT INTO `evolucionpaciente` (idPaciente, estadoEmocional, nivelEnergia, notasPersonales)
    VALUES (p_paciente, p_estadoEmocional, p_nivelEnergia, p_notas);
END$$

DELIMITER ;

-- --------------------------------------------------------
-- TABLAS
-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auditoriaaccesos`
--

CREATE TABLE `auditoriaaccesos` (
  `idAuditoria` int(11) NOT NULL,
  `idUsuario` int(11) NOT NULL,
  `accion` varchar(100) DEFAULT NULL,
  `ip` varchar(50) DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `autorizacionesdocumento`
--

CREATE TABLE `autorizacionesdocumento` (
  `idAutorizacion` int(11) NOT NULL,
  `idDocumento` int(11) NOT NULL,
  `idProfesional` int(11) NOT NULL,
  `fechaAutorizacion` datetime DEFAULT current_timestamp(),
  `revocado` tinyint(1) DEFAULT 0,
  `fechaRevocacion` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `citas`
--

CREATE TABLE `citas` (
  `idCita` int(11) NOT NULL,
  `idPaciente` int(11) NOT NULL,
  `idProfesional` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `hora` time NOT NULL,
  `tipoCita` varchar(80) DEFAULT NULL,
  `tipoSesion` varchar(80) DEFAULT NULL,
  `motivo` text DEFAULT NULL,
  `notas` text DEFAULT NULL,
  `estado` enum('Pendiente','Completada','Cancelada') DEFAULT 'Pendiente'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `conversacioneschatbot`
--

CREATE TABLE `conversacioneschatbot` (
  `idConversacion` int(11) NOT NULL,
  `idPaciente` int(11) NOT NULL,
  `mensajeUsuario` text DEFAULT NULL,
  `respuestaChatbot` text DEFAULT NULL,
  `nivelEmocionalDetectado` varchar(50) DEFAULT NULL,
  `palabrasRiesgoDetectadas` text DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `disponibilidad`
--

CREATE TABLE `disponibilidad` (
  `idDisponibilidad` int(11) NOT NULL,
  `idProfesional` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `hora_inicio` time NOT NULL,
  `hora_fin` time NOT NULL,
  `estado` enum('Disponible','Bloqueado') DEFAULT 'Disponible'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `documentosclinicos`
--

CREATE TABLE `documentosclinicos` (
  `idDocumento` int(11) NOT NULL,
  `idProfesional` int(11) NOT NULL,
  `idPaciente` int(11) NOT NULL,
  `nombreArchivo` varchar(255) NOT NULL,
  `rutaArchivo` varchar(500) NOT NULL,
  `tipoMime` varchar(100) DEFAULT NULL,
  `tamanoArchivo` int(11) DEFAULT NULL,
  `categoria` enum('Historia Clinica','Evolucion','Diagnostico','Consentimiento','Otro') DEFAULT 'Otro',
  `visibilidad` enum('privado','compartido') DEFAULT 'privado',
  `notasInternas` text DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp(),
  `eliminado` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `documentospaciente`
--

CREATE TABLE `documentospaciente` (
  `idDocumento` int(11) NOT NULL,
  `idPaciente` int(11) NOT NULL,
  `nombreArchivo` varchar(255) NOT NULL,
  `rutaArchivo` varchar(500) NOT NULL,
  `tipoMime` varchar(100) DEFAULT NULL,
  `tamanoArchivo` int(11) DEFAULT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp(),
  `eliminado` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `evolucionpaciente`
--

CREATE TABLE `evolucionpaciente` (
  `idEvolucion` int(11) NOT NULL,
  `idPaciente` int(11) NOT NULL,
  `idConversacion` int(11) DEFAULT NULL,
  `estadoEmocional` varchar(100) DEFAULT NULL,
  `nivelEnergia` int(11) DEFAULT NULL,
  `notasPersonales` text DEFAULT NULL,
  `resultadoEmocional` varchar(100) DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `facturas`
--

CREATE TABLE `facturas` (
  `idFactura` int(11) NOT NULL,
  `idPaciente` int(11) NOT NULL,
  `idProfesional` int(11) NOT NULL,
  `idCita` int(11) DEFAULT NULL,
  `monto` decimal(10,2) DEFAULT NULL,
  `metodoPago` enum('banco','tarjeta') DEFAULT 'tarjeta',
  `estadoPago` enum('Pendiente','Pagado') DEFAULT 'Pendiente',
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `itemsfactura`
--

CREATE TABLE `itemsfactura` (
  `idItem` int(11) NOT NULL,
  `idFactura` int(11) NOT NULL,
  `descripcion` varchar(120) DEFAULT NULL,
  `precioUnitario` decimal(10,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `login`
--

CREATE TABLE `login` (
  `idLogin` int(11) NOT NULL,
  `idUsuario` int(11) NOT NULL,
  `email` varchar(120) NOT NULL,
  `contrasena` varchar(200) NOT NULL,
  `ultimoAcceso` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `logs`
--

CREATE TABLE `logs` (
  `idLog` int(11) NOT NULL,
  `administrador` varchar(120) DEFAULT NULL,
  `modulo` varchar(80) DEFAULT NULL,
  `accion` varchar(120) DEFAULT NULL,
  `detalle` text DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `notificaciones`
--

CREATE TABLE `notificaciones` (
  `idNotificacion` int(11) NOT NULL,
  `idUsuario` int(11) DEFAULT NULL,
  `titulo` varchar(200) DEFAULT NULL,
  `mensaje` text DEFAULT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `destinatario` varchar(80) DEFAULT NULL,
  `email_individual` varchar(120) DEFAULT NULL,
  `enviado_por` varchar(120) DEFAULT NULL,
  `estado` enum('enviado','pendiente') DEFAULT 'enviado',
  `leido` tinyint(1) DEFAULT 0,
  `fecha` datetime DEFAULT current_timestamp(),
  `fecha_programada` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pacientesprofesional`
--

CREATE TABLE `pacientesprofesional` (
  `idRegistro` int(11) NOT NULL,
  `idProfesional` int(11) NOT NULL,
  `idPaciente` int(11) DEFAULT NULL,
  `nombre` varchar(120) DEFAULT NULL,
  `edad` int(11) DEFAULT NULL,
  `sexo` varchar(20) DEFAULT NULL,
  `contacto` varchar(120) DEFAULT NULL,
  `direccion` text DEFAULT NULL,
  `notas` text DEFAULT NULL,
  `sintomas` text DEFAULT NULL,
  `diagnostico` text DEFAULT NULL,
  `tratamiento` text DEFAULT NULL,
  `fechaDiagnostico` date DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `perfilpaciente`
--

CREATE TABLE `perfilpaciente` (
  `idPaciente` int(11) NOT NULL,
  `edad` int(11) DEFAULT NULL,
  `genero` varchar(20) DEFAULT NULL,
  `numeroTelefonico` varchar(20) DEFAULT NULL,
  `consentimientoDatos` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `perfilprofesional`
--

CREATE TABLE `perfilprofesional` (
  `idProfesional` int(11) NOT NULL,
  `especialidad` varchar(120) DEFAULT NULL,
  `licencia` varchar(120) DEFAULT NULL,
  `experiencia` text DEFAULT NULL,
  `estado` enum('Activo','Inactivo') DEFAULT 'Activo'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `register`
--

CREATE TABLE `register` (
  `idUsuario` int(11) NOT NULL,
  `nombre` varchar(120) NOT NULL,
  `email` varchar(120) NOT NULL,
  `contrasena` varchar(200) NOT NULL,
  `rol` enum('paciente','profesional','admin') NOT NULL,
  `fotoPerfil` varchar(255) DEFAULT NULL,
  `estadoCuenta` enum('Activa','Suspendida') DEFAULT 'Activa',
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  `fechaRegistro` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `reportes`
--

CREATE TABLE `reportes` (
  `idReporte` int(11) NOT NULL,
  `idProfesional` int(11) NOT NULL,
  `idPaciente` int(11) DEFAULT NULL,
  `tipoReporte` varchar(80) DEFAULT NULL,
  `fechaInicio` date DEFAULT NULL,
  `fechaFin` date DEFAULT NULL,
  `estado` enum('Pendiente','Completado') DEFAULT 'Pendiente',
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- DISPARADORES (TRIGGERS)
-- --------------------------------------------------------

DELIMITER $$

CREATE TRIGGER `trg_registrar_reactivacion` AFTER UPDATE ON `register` FOR EACH ROW BEGIN
    IF NEW.estadoCuenta = 'Activa' AND OLD.estadoCuenta = 'Suspendida' THEN
        INSERT INTO `auditoriaaccesos` (idUsuario, accion, ip)
        VALUES (NEW.idUsuario, 'Reactivación de cuenta', '0.0.0.0');
    END IF;
END$$

CREATE TRIGGER `trg_cita_notificacion_paciente` AFTER INSERT ON `citas` FOR EACH ROW BEGIN
    INSERT INTO `notificaciones` (idUsuario, titulo, mensaje, tipo, estado, enviado_por)
    VALUES (NEW.idPaciente, 'Nueva cita', 'Se ha programado una nueva cita.', 'Cita', 'enviado', 'Sistema');
END$$

CREATE TRIGGER `trg_cita_notificacion_profesional` AFTER INSERT ON `citas` FOR EACH ROW BEGIN
    INSERT INTO `notificaciones` (idUsuario, titulo, mensaje, tipo, estado, enviado_por)
    VALUES (NEW.idProfesional, 'Nueva cita agendada', 'Tienes una nueva cita agendada.', 'Cita', 'enviado', 'Sistema');
END$$

CREATE TRIGGER `trg_evitar_factura_duplicada` BEFORE INSERT ON `facturas` FOR EACH ROW BEGIN
    IF EXISTS (
        SELECT 1 FROM `facturas`
        WHERE idPaciente = NEW.idPaciente
          AND DATE(fecha) = CURDATE()
          AND idCita = NEW.idCita
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ya existe una factura para esta cita hoy.';
    END IF;
END$$

CREATE TRIGGER `trg_evolucion_notificacion` AFTER INSERT ON `evolucionpaciente` FOR EACH ROW BEGIN
    INSERT INTO `notificaciones` (idUsuario, titulo, mensaje, tipo, estado, enviado_por)
    VALUES (NEW.idPaciente, 'Evolución registrada', 'Se ha registrado tu nueva evolución emocional.', 'Evolución', 'enviado', 'Sistema');
END$$

CREATE TRIGGER `trg_alerta_emocional` AFTER INSERT ON `conversacioneschatbot` FOR EACH ROW BEGIN
    IF NEW.nivelEmocionalDetectado = 'Alto' THEN
        INSERT INTO `notificaciones` (idUsuario, mensaje, tipo, estado)
        VALUES (
            NEW.idPaciente,
            'Se detectó un estado emocional crítico. Un profesional revisará tu caso.',
            'Alerta',
            'enviado'
        );
    END IF;
END$$

DELIMITER ;

-- --------------------------------------------------------
-- VISTAS (Stand-in structures)
-- --------------------------------------------------------

CREATE TABLE `vistacitaspendientes` (
`idCita` int(11)
,`paciente` varchar(120)
,`fecha` date
,`hora` time
,`tipoCita` varchar(80)
,`tipoSesion` varchar(80)
,`motivo` text
,`notas` text
,`estado` enum('Pendiente','Completada','Cancelada')
);

CREATE TABLE `vistaevolucionpaciente` (
`nombre` varchar(120)
,`estadoEmocional` varchar(100)
,`nivelEnergia` int(11)
,`notasPersonales` text
,`fecha` datetime
);

CREATE TABLE `vistafacturacion` (
`idFactura` int(11)
,`paciente` varchar(120)
,`monto` decimal(10,2)
,`metodoPago` enum('banco','tarjeta')
,`estadoPago` enum('Pendiente','Pagado')
,`fecha` datetime
);

CREATE TABLE `vistahistorialchatbot` (
`nombre` varchar(120)
,`mensajeUsuario` text
,`respuestaChatbot` text
,`nivelEmocionalDetectado` varchar(50)
,`fecha` datetime
);

CREATE TABLE `vistalogsadmin` (
`id` int(11)
,`administrador` varchar(120)
,`modulo` varchar(80)
,`accion` varchar(120)
,`detalle` mediumtext
,`fecha` varchar(21)
,`origen` varchar(9)
);

CREATE TABLE `vistareportes` (
`idReporte` int(11)
,`profesional` varchar(120)
,`paciente` varchar(120)
,`tipoReporte` varchar(80)
,`fechaInicio` date
,`fechaFin` date
,`estado` enum('Pendiente','Completado')
,`fecha` datetime
);

-- --------------------------------------------------------
-- ÍNDICES Y AUTO_INCREMENT
-- --------------------------------------------------------

--
-- Índices de la tabla `auditoriaaccesos`
--
ALTER TABLE `auditoriaaccesos`
  ADD PRIMARY KEY (`idAuditoria`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Índices de la tabla `autorizacionesdocumento`
--
ALTER TABLE `autorizacionesdocumento`
  ADD PRIMARY KEY (`idAutorizacion`),
  ADD UNIQUE KEY `uq_doc_prof` (`idDocumento`,`idProfesional`),
  ADD KEY `idx_profesional` (`idProfesional`);

--
-- Índices de la tabla `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`idCita`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idProfesional` (`idProfesional`);

--
-- Índices de la tabla `conversacioneschatbot`
--
ALTER TABLE `conversacioneschatbot`
  ADD PRIMARY KEY (`idConversacion`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- Índices de la tabla `disponibilidad`
--
ALTER TABLE `disponibilidad`
  ADD PRIMARY KEY (`idDisponibilidad`),
  ADD KEY `idProfesional` (`idProfesional`);

--
-- Índices de la tabla `documentosclinicos`
--
ALTER TABLE `documentosclinicos`
  ADD PRIMARY KEY (`idDocumento`),
  ADD KEY `idx_profesional` (`idProfesional`),
  ADD KEY `idx_paciente` (`idPaciente`);

--
-- Índices de la tabla `documentospaciente`
--
ALTER TABLE `documentospaciente`
  ADD PRIMARY KEY (`idDocumento`),
  ADD KEY `idx_paciente` (`idPaciente`);

--
-- Índices de la tabla `evolucionpaciente`
--
ALTER TABLE `evolucionpaciente`
  ADD PRIMARY KEY (`idEvolucion`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idConversacion` (`idConversacion`);

--
-- Índices de la tabla `facturas`
--
ALTER TABLE `facturas`
  ADD PRIMARY KEY (`idFactura`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idCita` (`idCita`);

--
-- Índices de la tabla `itemsfactura`
--
ALTER TABLE `itemsfactura`
  ADD PRIMARY KEY (`idItem`),
  ADD KEY `idFactura` (`idFactura`);

--
-- Índices de la tabla `login`
--
ALTER TABLE `login`
  ADD PRIMARY KEY (`idLogin`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Índices de la tabla `logs`
--
ALTER TABLE `logs`
  ADD PRIMARY KEY (`idLog`);

--
-- Índices de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  ADD PRIMARY KEY (`idNotificacion`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Índices de la tabla `pacientesprofesional`
--
ALTER TABLE `pacientesprofesional`
  ADD PRIMARY KEY (`idRegistro`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- Índices de la tabla `perfilpaciente`
--
ALTER TABLE `perfilpaciente`
  ADD PRIMARY KEY (`idPaciente`);

--
-- Índices de la tabla `perfilprofesional`
--
ALTER TABLE `perfilprofesional`
  ADD PRIMARY KEY (`idProfesional`);

--
-- Índices de la tabla `register`
--
ALTER TABLE `register`
  ADD PRIMARY KEY (`idUsuario`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Índices de la tabla `reportes`
--
ALTER TABLE `reportes`
  ADD PRIMARY KEY (`idReporte`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- AUTO_INCREMENT de las tablas
--

ALTER TABLE `auditoriaaccesos`
  MODIFY `idAuditoria` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `autorizacionesdocumento`
  MODIFY `idAutorizacion` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `citas`
  MODIFY `idCita` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `conversacioneschatbot`
  MODIFY `idConversacion` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `disponibilidad`
  MODIFY `idDisponibilidad` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `documentosclinicos`
  MODIFY `idDocumento` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `documentospaciente`
  MODIFY `idDocumento` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `evolucionpaciente`
  MODIFY `idEvolucion` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `facturas`
  MODIFY `idFactura` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `itemsfactura`
  MODIFY `idItem` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `login`
  MODIFY `idLogin` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `logs`
  MODIFY `idLog` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `notificaciones`
  MODIFY `idNotificacion` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `pacientesprofesional`
  MODIFY `idRegistro` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `register`
  MODIFY `idUsuario` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

ALTER TABLE `reportes`
  MODIFY `idReporte` int(11) NOT NULL AUTO_INCREMENT;

-- --------------------------------------------------------
-- RESTRICCIONES (FOREIGN KEYS)
-- --------------------------------------------------------

ALTER TABLE `auditoriaaccesos`
  ADD CONSTRAINT `auditoriaaccesos_ibfk_1` FOREIGN KEY (`idUsuario`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `autorizacionesdocumento`
  ADD CONSTRAINT `autdoc_ibfk_1` FOREIGN KEY (`idDocumento`) REFERENCES `documentospaciente` (`idDocumento`) ON DELETE CASCADE,
  ADD CONSTRAINT `autdoc_ibfk_2` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `citas`
  ADD CONSTRAINT `citas_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `citas_ibfk_2` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `conversacioneschatbot`
  ADD CONSTRAINT `conversacioneschatbot_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `disponibilidad`
  ADD CONSTRAINT `disponibilidad_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `documentosclinicos`
  ADD CONSTRAINT `docclin_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `docclin_ibfk_2` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `documentospaciente`
  ADD CONSTRAINT `docpac_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `evolucionpaciente`
  ADD CONSTRAINT `evolucionpaciente_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `evolucionpaciente_ibfk_2` FOREIGN KEY (`idConversacion`) REFERENCES `conversacioneschatbot` (`idConversacion`) ON DELETE SET NULL;

ALTER TABLE `facturas`
  ADD CONSTRAINT `facturas_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `facturas_ibfk_2` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `facturas_ibfk_3` FOREIGN KEY (`idCita`) REFERENCES `citas` (`idCita`) ON DELETE SET NULL;

ALTER TABLE `itemsfactura`
  ADD CONSTRAINT `itemsfactura_ibfk_1` FOREIGN KEY (`idFactura`) REFERENCES `facturas` (`idFactura`) ON DELETE CASCADE;

ALTER TABLE `login`
  ADD CONSTRAINT `login_ibfk_1` FOREIGN KEY (`idUsuario`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `notificaciones`
  ADD CONSTRAINT `notificaciones_ibfk_1` FOREIGN KEY (`idUsuario`) REFERENCES `register` (`idUsuario`) ON DELETE SET NULL;

ALTER TABLE `pacientesprofesional`
  ADD CONSTRAINT `pacientesprofesional_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `pacientesprofesional_ibfk_2` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE SET NULL;

ALTER TABLE `perfilpaciente`
  ADD CONSTRAINT `perfilpaciente_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `perfilprofesional`
  ADD CONSTRAINT `perfilprofesional_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

ALTER TABLE `reportes`
  ADD CONSTRAINT `reportes_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `reportes_ibfk_2` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE SET NULL;

-- --------------------------------------------------------
-- VISTAS REALES
-- --------------------------------------------------------

DROP TABLE IF EXISTS `vistacitaspendientes`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistacitaspendientes` AS
SELECT 
    c.`idCita` AS `idCita`,
    u.`nombre` AS `paciente`,
    c.`fecha` AS `fecha`,
    c.`hora` AS `hora`,
    c.`tipoCita` AS `tipoCita`,
    c.`tipoSesion` AS `tipoSesion`,
    c.`motivo` AS `motivo`,
    c.`notas` AS `notas`,
    c.`estado` AS `estado`
FROM `citas` c
JOIN `register` u ON c.`idPaciente` = u.`idUsuario`
WHERE c.`estado` = 'Pendiente';

DROP TABLE IF EXISTS `vistaevolucionpaciente`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistaevolucionpaciente` AS
SELECT 
    u.`nombre` AS `nombre`,
    e.`estadoEmocional` AS `estadoEmocional`,
    e.`nivelEnergia` AS `nivelEnergia`,
    e.`notasPersonales` AS `notasPersonales`,
    e.`fecha` AS `fecha`
FROM `evolucionpaciente` e
JOIN `register` u ON e.`idPaciente` = u.`idUsuario`;

DROP TABLE IF EXISTS `vistafacturacion`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistafacturacion` AS
SELECT 
    f.`idFactura` AS `idFactura`,
    u.`nombre` AS `paciente`,
    f.`monto` AS `monto`,
    f.`metodoPago` AS `metodoPago`,
    f.`estadoPago` AS `estadoPago`,
    f.`fecha` AS `fecha`
FROM `facturas` f
JOIN `register` u ON f.`idPaciente` = u.`idUsuario`;

DROP TABLE IF EXISTS `vistahistorialchatbot`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistahistorialchatbot` AS
SELECT 
    u.`nombre` AS `nombre`,
    c.`mensajeUsuario` AS `mensajeUsuario`,
    c.`respuestaChatbot` AS `respuestaChatbot`,
    c.`nivelEmocionalDetectado` AS `nivelEmocionalDetectado`,
    c.`fecha` AS `fecha`
FROM `conversacioneschatbot` c
JOIN `register` u ON c.`idPaciente` = u.`idUsuario`;

DROP TABLE IF EXISTS `vistalogsadmin`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistalogsadmin` AS
SELECT 
    l.`idLog` AS `id`,
    l.`administrador` AS `administrador`,
    l.`modulo` AS `modulo`,
    l.`accion` AS `accion`,
    l.`detalle` AS `detalle`,
    DATE_FORMAT(l.`fecha`, '%d/%m/%Y %H:%i') AS `fecha`,
    'admin' AS `origen`
FROM `logs` l
UNION ALL
SELECT 
    a.`idAuditoria` AS `id`,
    COALESCE(r.`nombre`, CONCAT('Usuario #', a.`idUsuario`)) AS `administrador`,
    'accesos' AS `modulo`,
    a.`accion` AS `accion`,
    CONCAT('IP: ', a.`ip`) AS `detalle`,
    DATE_FORMAT(a.`fecha`, '%d/%m/%Y %H:%i') AS `fecha`,
    'auditoria' AS `origen`
FROM `auditoriaaccesos` a
LEFT JOIN `register` r ON a.`idUsuario` = r.`idUsuario`;

DROP TABLE IF EXISTS `vistareportes`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistareportes` AS
SELECT 
    r.`idReporte` AS `idReporte`,
    up.`nombre` AS `profesional`,
    ua.`nombre` AS `paciente`,
    r.`tipoReporte` AS `tipoReporte`,
    r.`fechaInicio` AS `fechaInicio`,
    r.`fechaFin` AS `fechaFin`,
    r.`estado` AS `estado`,
    r.`fecha` AS `fecha`
FROM `reportes` r
JOIN `register` up ON r.`idProfesional` = up.`idUsuario`
LEFT JOIN `register` ua ON r.`idPaciente` = ua.`idUsuario`;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

-- ============================================================
-- CREDENCIALES DE PRUEBA
-- ============================================================
-- Admin:       admin@psyai.com      / admin123
-- Profesional: profesional@psyai.com / profesional123
-- Paciente:    paciente@psyai.com   / paciente123
-- ============================================================

START TRANSACTION;

INSERT INTO register
    (idUsuario, nombre, email, contrasena, rol,
     estadoCuenta, activo, email_verificado, fechaRegistro)
VALUES
    (1, 'Paciente Demo', 'paciente@psyai.com',
     'argon2$argon2id$v=19$m=102400,t=2,p=8$a0lwcDJSdTFvaGJDcjd0N3lHWlhuTw$nJAHoFaURwoaGgSB6hI8LnDjUPA6mF45cvlWy/5H3is',
     'paciente', 'Activa', 1, 1, NOW()),
    (2, 'Profesional Demo', 'profesional@psyai.com',
     'argon2$argon2id$v=19$m=102400,t=2,p=8$QVVYemNlNUdYM0U5V0NrOG5ycEpOWA$QJ4Ad6luFU9mfyNpmHga/O9nEqbuPfeQl5+1I651BOg',
     'profesional', 'Activa', 1, 1, NOW()),
    (3, 'Administrador', 'admin@psyai.com',
     'argon2$argon2id$v=19$m=102400,t=2,p=8$aVVqZUR2RE5BSDRLWW9uSXhudnRoZw$yaDAPJb6FDenDGa14N6Dr5xwM2DJKknzkT+KkAhoUlc',
     'admin', 'Activa', 1, 1, NOW());

INSERT INTO perfilpaciente
    (idPaciente, edad, genero, numeroTelefonico, consentimientoDatos)
VALUES
    (1, 25, 'Femenino', NULL, 0);

INSERT INTO perfilprofesional
    (idProfesional, especialidad, experiencia, estado)
VALUES
    (2, 'Psicología Clínica', 'Profesional demo', 'Activo');

COMMIT;
