-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generaciÃ³n: 26-10-2026
-- VersiÃ³n del servidor: 10.4.32-MariaDB
-- VersiÃ³n de PHP: 8.2.12

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
  `fecha` datetime DEFAULT current_timestamp(),
  `origen` varchar(20) DEFAULT 'admin'
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
        VALUES (NEW.idUsuario, 'ReactivaciÃ³n de cuenta', '0.0.0.0');
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
    VALUES (NEW.idPaciente, 'EvoluciÃ³n registrada', 'Se ha registrado tu nueva evoluciÃ³n emocional.', 'EvoluciÃ³n', 'enviado', 'Sistema');
END$$

CREATE TRIGGER `trg_alerta_emocional` AFTER INSERT ON `conversacioneschatbot` FOR EACH ROW BEGIN
    IF NEW.nivelEmocionalDetectado = 'Alto' THEN
        INSERT INTO `notificaciones` (idUsuario, mensaje, tipo, estado)
        VALUES (
            NEW.idPaciente,
            'Se detectÃ³ un estado emocional crÃ­tico. Un profesional revisarÃ¡ tu caso.',
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
-- ÃNDICES Y AUTO_INCREMENT
-- --------------------------------------------------------

--
-- Ãndices de la tabla `auditoriaaccesos`
--
ALTER TABLE `auditoriaaccesos`
  ADD PRIMARY KEY (`idAuditoria`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Ãndices de la tabla `autorizacionesdocumento`
--
ALTER TABLE `autorizacionesdocumento`
  ADD PRIMARY KEY (`idAutorizacion`),
  ADD UNIQUE KEY `uq_doc_prof` (`idDocumento`,`idProfesional`),
  ADD KEY `idx_profesional` (`idProfesional`);

--
-- Ãndices de la tabla `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`idCita`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idProfesional` (`idProfesional`);

--
-- Ãndices de la tabla `conversacioneschatbot`
--
ALTER TABLE `conversacioneschatbot`
  ADD PRIMARY KEY (`idConversacion`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- Ãndices de la tabla `disponibilidad`
--
ALTER TABLE `disponibilidad`
  ADD PRIMARY KEY (`idDisponibilidad`),
  ADD KEY `idProfesional` (`idProfesional`);

--
-- Ãndices de la tabla `documentosclinicos`
--
ALTER TABLE `documentosclinicos`
  ADD PRIMARY KEY (`idDocumento`),
  ADD KEY `idx_profesional` (`idProfesional`),
  ADD KEY `idx_paciente` (`idPaciente`);

--
-- Ãndices de la tabla `documentospaciente`
--
ALTER TABLE `documentospaciente`
  ADD PRIMARY KEY (`idDocumento`),
  ADD KEY `idx_paciente` (`idPaciente`);

--
-- Ãndices de la tabla `evolucionpaciente`
--
ALTER TABLE `evolucionpaciente`
  ADD PRIMARY KEY (`idEvolucion`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idConversacion` (`idConversacion`);

--
-- Ãndices de la tabla `facturas`
--
ALTER TABLE `facturas`
  ADD PRIMARY KEY (`idFactura`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idCita` (`idCita`);

--
-- Ãndices de la tabla `itemsfactura`
--
ALTER TABLE `itemsfactura`
  ADD PRIMARY KEY (`idItem`),
  ADD KEY `idFactura` (`idFactura`);

--
-- Ãndices de la tabla `login`
--
ALTER TABLE `login`
  ADD PRIMARY KEY (`idLogin`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Ãndices de la tabla `logs`
--
ALTER TABLE `logs`
  ADD PRIMARY KEY (`idLog`);

--
-- Ãndices de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  ADD PRIMARY KEY (`idNotificacion`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Ãndices de la tabla `pacientesprofesional`
--
ALTER TABLE `pacientesprofesional`
  ADD PRIMARY KEY (`idRegistro`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- Ãndices de la tabla `perfilpaciente`
--
ALTER TABLE `perfilpaciente`
  ADD PRIMARY KEY (`idPaciente`);

--
-- Ãndices de la tabla `perfilprofesional`
--
ALTER TABLE `perfilprofesional`
  ADD PRIMARY KEY (`idProfesional`);

--
-- Ãndices de la tabla `register`
--
ALTER TABLE `register`
  ADD PRIMARY KEY (`idUsuario`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Ãndices de la tabla `reportes`
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
    COALESCE(l.`origen`, 'admin') AS `origen`
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
    (2, 'PsicologÃ­a ClÃ­nica', 'Profesional demo', 'Activo');

COMMIT;
m y s q l d u m p   :   m y s q l d u m p :   [ W a r n i n g ]   U s i n g   a   p a s s w o r d   o n   t h e   c o m m a n d   l i n e   i n t e r f a c e   c a n   b e   i n s e c u r e .  
 E n   l í n e a :   1   C a r á c t e r :   1  
 +   m y s q l d u m p   - u   r o o t   - p r o o t   p s y a i _ c o n n e c t   R e g i s t e r   >   " C : \ U s e r s \ M a n u e l   R o   . . .  
 +   ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~  
         +   C a t e g o r y I n f o                     :   N o t S p e c i f i e d :   ( m y s q l d u m p :   [ W a r . . . a n   b e   i n s e c u r e . : S t r i n g )   [ ] ,   R e m o t e E x c e p t i o n  
         +   F u l l y Q u a l i f i e d E r r o r I d   :   N a t i v e C o m m a n d E r r o r  
    
 - -   M y S Q L   d u m p   1 0 . 1 3     D i s t r i b   8 . 0 . 4 6 ,   f o r   W i n 6 4   ( x 8 6 _ 6 4 )  
 - -  
 - -   H o s t :   l o c a l h o s t         D a t a b a s e :   p s y a i _ c o n n e c t  
 - -   - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  
 - -   S e r v e r   v e r s i o n 	 8 . 0 . 4 6  
  
 / * ! 4 0 1 0 1   S E T   @ O L D _ C H A R A C T E R _ S E T _ C L I E N T = @ @ C H A R A C T E R _ S E T _ C L I E N T   * / ;  
 / * ! 4 0 1 0 1   S E T   @ O L D _ C H A R A C T E R _ S E T _ R E S U L T S = @ @ C H A R A C T E R _ S E T _ R E S U L T S   * / ;  
 / * ! 4 0 1 0 1   S E T   @ O L D _ C O L L A T I O N _ C O N N E C T I O N = @ @ C O L L A T I O N _ C O N N E C T I O N   * / ;  
 / * ! 5 0 5 0 3   S E T   N A M E S   u t f 8 m b 4   * / ;  
 / * ! 4 0 1 0 3   S E T   @ O L D _ T I M E _ Z O N E = @ @ T I M E _ Z O N E   * / ;  
 / * ! 4 0 1 0 3   S E T   T I M E _ Z O N E = ' + 0 0 : 0 0 '   * / ;  
 / * ! 4 0 0 1 4   S E T   @ O L D _ U N I Q U E _ C H E C K S = @ @ U N I Q U E _ C H E C K S ,   U N I Q U E _ C H E C K S = 0   * / ;  
 / * ! 4 0 0 1 4   S E T   @ O L D _ F O R E I G N _ K E Y _ C H E C K S = @ @ F O R E I G N _ K E Y _ C H E C K S ,   F O R E I G N _ K E Y _ C H E C K S = 0   * / ;  
 / * ! 4 0 1 0 1   S E T   @ O L D _ S Q L _ M O D E = @ @ S Q L _ M O D E ,   S Q L _ M O D E = ' N O _ A U T O _ V A L U E _ O N _ Z E R O '   * / ;  
 / * ! 4 0 1 1 1   S E T   @ O L D _ S Q L _ N O T E S = @ @ S Q L _ N O T E S ,   S Q L _ N O T E S = 0   * / ;  
  
 - -  
 - -   T a b l e   s t r u c t u r e   f o r   t a b l e   ` r e g i s t e r `  
 - -  
  
 D R O P   T A B L E   I F   E X I S T S   ` r e g i s t e r ` ;  
 / * ! 4 0 1 0 1   S E T   @ s a v e d _ c s _ c l i e n t           =   @ @ c h a r a c t e r _ s e t _ c l i e n t   * / ;  
 / * ! 5 0 5 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   u t f 8 m b 4   * / ;  
 C R E A T E   T A B L E   ` r e g i s t e r `   (  
     ` i d U s u a r i o `   i n t   N O T   N U L L   A U T O _ I N C R E M E N T ,  
     ` n o m b r e `   v a r c h a r ( 1 2 0 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` e m a i l `   v a r c h a r ( 1 2 0 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` c o n t r a s e n a `   v a r c h a r ( 2 5 5 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` r o l `   e n u m ( ' p a c i e n t e ' , ' p r o f e s i o n a l ' , ' a d m i n ' )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` f o t o P e r f i l `   v a r c h a r ( 2 5 5 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   D E F A U L T   N U L L ,  
     ` e s t a d o C u e n t a `   e n u m ( ' A c t i v a ' , ' S u s p e n d i d a ' )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   D E F A U L T   ' A c t i v a ' ,  
     ` a c t i v o `   t i n y i n t ( 1 )   N O T   N U L L   D E F A U L T   ' 1 ' ,  
     ` f e c h a R e g i s t r o `   d a t e t i m e   D E F A U L T   C U R R E N T _ T I M E S T A M P ,  
     ` p a s s w o r d `   v a r c h a r ( 1 2 8 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` l a s t _ l o g i n `   d a t e t i m e ( 6 )   D E F A U L T   N U L L ,  
     ` e m a i l _ v e r i f i c a d o `   t i n y i n t ( 1 )   N O T   N U L L ,  
     P R I M A R Y   K E Y   ( ` i d U s u a r i o ` ) ,  
     U N I Q U E   K E Y   ` e m a i l `   ( ` e m a i l ` )  
 )   E N G I N E = I n n o D B   A U T O _ I N C R E M E N T = 3 4   D E F A U L T   C H A R S E T = u t f 8 m b 4   C O L L A T E = u t f 8 m b 4 _ u n i c o d e _ c i ;  
 / * ! 4 0 1 0 1   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   @ s a v e d _ c s _ c l i e n t   * / ;  
  
 - -  
 - -   D u m p i n g   d a t a   f o r   t a b l e   ` r e g i s t e r `  
 - -  
  
 L O C K   T A B L E S   ` r e g i s t e r `   W R I T E ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` r e g i s t e r `   D I S A B L E   K E Y S   * / ;  
 I N S E R T   I N T O   ` r e g i s t e r `   V A L U E S   ( 1 , ' A d m i n i s t r a d o r ' , ' a d m i n @ p s y a i . c o m ' , ' 6 0 f e 7 4 4 0 6 e 7 f 3 5 3 e d 9 7 9 f 3 5 0 f 2 f b b 6 a 2 e 8 6 9 0 a 5 f a 7 d 1 b 0 c 3 2 9 8 3 d 1 d 8 b 3 f 9 5 f 6 7 ' , ' a d m i n ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 5   1 6 : 1 6 : 1 9 ' , ' ' , N U L L , 0 ) , ( 2 , ' M a n u e l ' , ' p a c i e n t e @ g m a i l . c o m ' , ' $ 2 b $ 1 2 $ o I J d x x 1 G x p F Z L . H K E c O 7 M u d F 4 t x p A x q F 4 k S e a y K r S x . I 3 F O f y G s W y ' , ' p r o f e s i o n a l ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 7   1 2 : 5 3 : 3 2 ' , ' ' , N U L L , 0 ) , ( 3 , ' P r o f e s i o n a l ' , ' p r o f e s i o n a l @ p s y a i . c o m ' , ' 7 8 2 0 9 2 4 a d a b b c c 8 b e a c e 4 9 a 9 4 9 8 b 8 a e d 5 1 0 d f 4 2 7 8 0 4 c f 7 a 9 3 d 2 4 3 4 1 a b 7 d a a a 1 1 ' , ' p r o f e s i o n a l ' , ' 1 6 a 8 7 1 a 5 3 3 2 c 4 c 4 2 b 6 b a 4 8 b 1 3 4 9 d 3 7 8 0 . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 7   1 8 : 0 0 : 2 8 ' , ' ' , ' 2 0 2 6 - 1 0 - 2 7   0 2 : 4 2 : 4 4 . 9 6 5 0 1 7 ' , 0 ) , ( 4 , ' A d m i n 2 ' , ' a d m i n 2 @ p s y a i . c o m ' , ' 2 4 0 b e 5 1 8 f a b d 2 7 2 4 d d b 6 f 0 4 e e b 1 d a 5 9 6 7 4 4 8 d 7 e 8 3 1 c 0 8 c 8 f a 8 2 2 8 0 9 f 7 4 c 7 2 0 a 9 ' , ' a d m i n ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 7   1 8 : 0 0 : 2 8 ' , ' ' , ' 2 0 2 6 - 1 0 - 2 9   0 4 : 1 0 : 3 2 . 4 7 5 7 7 2 ' , 0 ) , ( 5 , ' M a n u e l 2 ' , ' p a c i e n t e 2 @ g m a i l . c o m ' , ' 2 9 9 f b b 4 5 5 c 4 2 2 3 9 c 8 6 d 2 e e 3 b 1 5 4 0 3 e d 1 b 4 6 8 2 5 9 e c a e d f 0 c 3 5 2 7 4 5 1 e 1 f 0 d 6 3 d 5 9 ' , ' p a c i e n t e ' , ' 0 e 0 6 a 3 0 f c 7 a d 4 4 3 7 9 b b a 7 9 b e b 2 d e 3 b f 6 . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 1 6   2 3 : 0 0 : 1 2 ' , ' ' , N U L L , 0 ) , ( 6 , ' t e s t ' , ' t e s t @ g m a i l . c o m ' , ' $ 2 b $ 1 2 $ F 9 4 l e F E v c 0 h p h 7 N 1 O 8 v x 5 u P X v p 7 . q v B q f o t o u Z g d S a V R f i 7 Y t y g w C ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 1 6   2 3 : 1 4 : 3 7 ' , ' ' , N U L L , 0 ) , ( 8 , ' M a n u e l ' , ' m a n @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , ' e a b d 7 a 0 e c 6 3 6 4 9 4 3 a 0 5 a f 5 8 d b 2 5 b 9 b e 5 . p n g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 0 3   0 1 : 5 0 : 1 6 ' , ' ' , N U L L , 0 ) , ( 1 0 , ' M a n u e l ' , ' t e s t 3 @ g m a i l . c o m ' , ' 8 d 9 6 9 e e f 6 e c a d 3 c 2 9 a 3 a 6 2 9 2 8 0 e 6 8 6 c f 0 c 3 f 5 d 5 a 8 6 a f f 3 c a 1 2 0 2 0 c 9 2 3 a d c 6 c 9 2 ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 1 2   0 1 : 3 0 : 3 6 ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ 3 o C H 9 y 5 e z S x c f D Z r W A K c Z j $ W o U M t S 0 R c E a I u W s 0 v 0 P A x 3 j / O j O Y u D s M q B 2 P E l D f 4 x A = ' , ' 2 0 2 6 - 1 0 - 2 7   0 5 : 3 8 : 0 5 . 4 1 5 6 1 1 ' , 0 ) , ( 1 1 , ' h o l a ' , ' h o l a @ g m a i l . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 1 2   0 3 : 1 3 : 3 7 ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ a 3 0 q 2 q w B K I 7 R X v H 0 r c 2 z z F $ g i 7 E X 6 f i j S w U G 1 b f 8 t L 5 J N V z f b u p U 5 H t K i 3 H p 5 t i K 0 c = ' , N U L L , 0 ) , ( 1 2 , ' t e s t ' , ' p a c i e n t e 3 @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , ' 6 3 8 9 4 d c f b d c 8 4 6 2 4 a 8 7 d f a 0 6 6 8 f a 4 1 5 e . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 1 2   0 3 : 3 6 : 1 8 ' , ' ! w J Q d 8 N p 1 n u F K f O H T 1 Y A n e w D y a w o m K t 5 t G l i a y k G k ' , ' 2 0 2 6 - 0 9 - 2 5   0 5 : 0 1 : 3 5 . 7 7 5 5 7 3 ' , 0 ) , ( 1 4 , ' M a n u e l   R o j a s ' , ' m a n u e l r o j a s q 2 1 @ g m a i l . c o m ' , ' 6 4 1 a e 3 5 4 f 6 0 6 4 e c c b 8 7 3 f 2 7 4 4 8 b 0 d c 3 b ' , ' p a c i e n t e ' , ' ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 1 4 : 4 6 ' , ' ! p P I d J 8 H N B g 5 A r 4 k V g Z B N j 5 l b 2 m E r 4 B d X e Z D q E o b w ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 1 4 : 4 6 . 1 9 7 1 4 0 ' , 0 ) , ( 1 5 , ' L e g e n d a r y G h o u l   W l ' , ' m a n o l o r o j a s 2 6 1 0 2 0 0 2 @ g m a i l . c o m ' , ' 5 7 f 8 1 7 1 9 a c a 8 4 d 1 5 8 5 2 5 1 6 9 d 3 2 6 9 3 1 a d ' , ' p a c i e n t e ' , ' ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 1 8 : 2 8 ' , ' ! W N L O G F Q H z G n 7 L a L n a k O L E U S L H d 1 x d k g O e 9 2 Q s w h k ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 3 6 : 4 0 . 2 3 4 9 3 8 ' , 0 ) , ( 1 6 , ' M a n u e l   R o j a s ' , ' m a n u e l a l e j a n d r o . r o j a s q u i n t e r o @ g m a i l . c o m ' , ' 8 6 7 f 2 7 6 c 4 7 1 8 4 b 7 0 a 1 1 8 d 7 4 4 2 1 d e e c 6 0 ' , ' p a c i e n t e ' , ' c 0 9 a 1 4 d f d c 2 4 4 1 d d a 6 d 2 b 6 f e 3 7 0 a d 6 0 a . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 1 : 1 6 ' , ' ! 6 P J s j P k 4 b j j q f p g c Y w q h Q j y m o A 7 6 h D X N j J 1 l Z O Q e ' , ' 2 0 2 6 - 0 8 - 0 5   0 3 : 2 6 : 2 1 . 4 6 5 0 1 0 ' , 0 ) , ( 1 7 , ' L e g e n d   P l u s   Ò â ä ' , ' m a n u e l r o j a s q u i n t e r o 7 0 0 @ g m a i l . c o m ' , ' 4 9 7 1 d a c 3 8 f f 0 4 b c c 9 5 a 3 8 7 4 4 a 2 7 4 5 1 0 b ' , ' p a c i e n t e ' , ' h t t p s : / / l h 3 . g o o g l e u s e r c o n t e n t . c o m / a / A C g 8 o c I 5 E 3 u o i X 1 7 l y x H Q p T 0 3 U y k 5 B 3 j D 9 G w P v H 8 0 m T _ 1 M d s B e k p E k F 9 = s 9 6 - c ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 9 : 0 5 ' , ' ! T c v h Y T w 7 R 5 a F s D r c b c X v Q K 9 h h m g V k B D F G n p k n 9 l W ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 9 : 0 4 . 6 4 8 6 8 5 ' , 0 ) , ( 1 8 , ' M a n u e l 2 ' , ' c u e n t a i n v e n t a d a @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 8 - 0 4   0 2 : 2 5 : 0 1 ' , ' ! 0 z E d J 3 R z D S F K P 0 C t u a q O Z J V h u K 9 6 4 l x h p P V i u h u 6 ' , N U L L , 0 ) , ( 1 9 , ' M a n u e l ' , ' r a n d o m @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 1 8   2 3 : 0 3 : 1 9 ' , ' ! j a V V r 3 d S p n g u W E 5 U m 8 L B 6 S f M L o B t n f 1 N i q h m V 9 d x ' , N U L L , 0 ) , ( 2 0 , ' H o l a   H O L A ' , ' m a n u e l a l e j a n d r o . r o j a s q u i n t e r o 3 @ g m a i l . c o m ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ o G 1 K t m w u N C H j J P P z N 0 W V q 3 $ 6 M g D 4 f F 6 Y f O P F H e + F c M 8 5 C H h 1 P f x P E 6 f h s + M h v c r I G 4 = ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 2 2   0 7 : 0 1 : 1 3 ' , ' ' , N U L L , 0 ) , ( 2 3 , ' n e p e   n e p e ' , ' a a a @ g m a i l . c o m ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ m J q k O C k e i q F s e q o q S t R 0 Q X $ N J K G s 7 Z u H y 1 s k Q U Z D n V M b Q o F k m J 8 q Q + P M 7 B T w w h 9 N Y A = ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 2 3   1 7 : 0 8 : 5 9 ' , ' ' , N U L L , 0 ) , ( 2 8 , ' M a n u e l 3 3 3 ' , ' t e s t e o @ g m a i l . c o m ' , ' a r g o n 2 $ a r g o n 2 i d $ v = 1 9 $ m = 1 0 2 4 0 0 , t = 2 , p = 8 $ N k Z y Y 1 F m c 2 1 P M F A 0 W F B P T 1 F 1 M E w x c g $ M K Q S F W 0 d s O V z N D S Y n g m 5 y f M E 7 c y b 6 8 2 i q E V w I p y 2 Q F U ' , ' p a c i e n t e ' , ' b 8 d 4 5 a 1 a 2 4 2 6 4 2 e a 9 0 2 8 0 0 b d 9 2 2 f 7 b 9 d . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 2 5   0 6 : 0 3 : 5 6 ' , ' ! P h l 2 Y Q 7 o v w 1 m v z N M 1 e l Z N x c B j x s T g L J C v b 8 5 O Q 8 z ' , ' 2 0 2 6 - 1 0 - 3 0   0 5 : 0 9 : 3 7 . 4 9 1 1 9 4 ' , 1 ) , ( 2 9 , ' T e s t   C h a t ' , ' t e s t c h a t @ t e s t . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 0 5 : 1 8 ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ E Y E K U d i 7 n P p a 8 w Q j M q k G H 8 $ 0 N y W A L v j 9 p x U a F G E B o a s e U w 0 W B j C 1 8 T H Q C F h n v + r h z s = ' , N U L L , 0 ) , ( 3 0 , ' T e s t   U s e r ' , ' t e s t 1 2 3 @ t e s t . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 3 6 : 1 9 ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ 0 1 E H 7 Y g y s B S 3 E m V 7 n J n n Q J $ 2 + + A k + 0 2 Z u A u x Q x 4 h x L Q m n a p c 3 R O N M R g D Z x x P l M Z L 3 c = ' , N U L L , 0 ) , ( 3 1 , ' T e s t 4 5 6 ' , ' t e s t 4 5 6 @ t e s t . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 3 6 : 4 7 ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ x h t L E 0 R 1 X z 3 d 2 T R U V q Z w t r $ y 5 6 e + Q u K 5 E R 4 e k O L A j i 8 7 / l F B u 3 L I B x d S X p L Y 9 u Z C W Q = ' , N U L L , 0 ) , ( 3 2 , ' T e s t 7 8 9 ' , ' t e s t 7 8 9 @ t e s t . c o m ' , ' b d 9 4 d c d a 2 6 f c c b 4 e 6 8 d 6 a 3 1 f 9 b 5 a a c 0 b 5 7 1 a e 2 6 6 d 8 2 2 6 2 0 e 9 0 1 e f 7 e b e 3 a 1 1 d 4 f ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 3 7 : 0 9 ' , ' ' , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 4 5 : 4 3 . 4 2 9 0 1 0 ' , 0 ) , ( 3 3 , ' s s   s s ' , ' t e s t e o 2 @ g m a i l . c o m ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ 5 8 e l T 7 9 m 2 L i U f 0 b n v m i 6 M h $ m y d Q b 9 C I b g p v 1 M z U q Y 7 d E A n Y / Q M u K P e G c H k O f 8 c S S 9 U = ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 7   0 6 : 3 7 : 1 4 ' , ' ' , N U L L , 0 ) ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` r e g i s t e r `   E N A B L E   K E Y S   * / ;  
 U N L O C K   T A B L E S ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ c s _ c l i e n t             =   @ @ c h a r a c t e r _ s e t _ c l i e n t   * /   ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ c s _ r e s u l t s           =   @ @ c h a r a c t e r _ s e t _ r e s u l t s   * /   ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ c o l _ c o n n e c t i o n   =   @ @ c o l l a t i o n _ c o n n e c t i o n   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t     =   u t f 8 m b 4   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ r e s u l t s   =   u t f 8 m b 4   * /   ;  
 / * ! 5 0 0 0 3   S E T   c o l l a t i o n _ c o n n e c t i o n     =   u t f 8 m b 4 _ 0 9 0 0 _ a i _ c i   * /   ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ s q l _ m o d e               =   @ @ s q l _ m o d e   * /   ;  
 / * ! 5 0 0 0 3   S E T   s q l _ m o d e                             =   ' N O _ A U T O _ V A L U E _ O N _ Z E R O '   * /   ;  
 D E L I M I T E R   ; ;  
 / * ! 5 0 0 0 3   C R E A T E * /   / * ! 5 0 0 1 7   D E F I N E R = ` r o o t ` @ ` l o c a l h o s t ` * /   / * ! 5 0 0 0 3   T R I G G E R   ` t r g _ r e g i s t r a r _ r e a c t i v a c i o n `   A F T E R   U P D A T E   O N   ` r e g i s t e r `   F O R   E A C H   R O W   B E G I N  
         I F   N E W . e s t a d o C u e n t a   =   ' A c t i v a '   A N D   O L D . e s t a d o C u e n t a   =   ' S u s p e n d i d a '   T H E N  
                 I N S E R T   I N T O   A u d i t o r i a A c c e s o s   ( i d U s u a r i o ,   a c c i o n ,   i p )  
                 V A L U E S   ( N E W . i d U s u a r i o ,   ' R e a c t i v a c i %%n   d e   c u e n t a ' ,   ' 0 . 0 . 0 . 0 ' ) ;  
         E N D   I F ;  
 E N D   * / ; ;  
 D E L I M I T E R   ;  
 / * ! 5 0 0 0 3   S E T   s q l _ m o d e                             =   @ s a v e d _ s q l _ m o d e   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t     =   @ s a v e d _ c s _ c l i e n t   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ r e s u l t s   =   @ s a v e d _ c s _ r e s u l t s   * /   ;  
 / * ! 5 0 0 0 3   S E T   c o l l a t i o n _ c o n n e c t i o n     =   @ s a v e d _ c o l _ c o n n e c t i o n   * /   ;  
 / * ! 4 0 1 0 3   S E T   T I M E _ Z O N E = @ O L D _ T I M E _ Z O N E   * / ;  
  
 / * ! 4 0 1 0 1   S E T   S Q L _ M O D E = @ O L D _ S Q L _ M O D E   * / ;  
 / * ! 4 0 0 1 4   S E T   F O R E I G N _ K E Y _ C H E C K S = @ O L D _ F O R E I G N _ K E Y _ C H E C K S   * / ;  
 / * ! 4 0 0 1 4   S E T   U N I Q U E _ C H E C K S = @ O L D _ U N I Q U E _ C H E C K S   * / ;  
 / * ! 4 0 1 0 1   S E T   C H A R A C T E R _ S E T _ C L I E N T = @ O L D _ C H A R A C T E R _ S E T _ C L I E N T   * / ;  
 / * ! 4 0 1 0 1   S E T   C H A R A C T E R _ S E T _ R E S U L T S = @ O L D _ C H A R A C T E R _ S E T _ R E S U L T S   * / ;  
 / * ! 4 0 1 0 1   S E T   C O L L A T I O N _ C O N N E C T I O N = @ O L D _ C O L L A T I O N _ C O N N E C T I O N   * / ;  
 / * ! 4 0 1 1 1   S E T   S Q L _ N O T E S = @ O L D _ S Q L _ N O T E S   * / ;  
  
 - -   D u m p   c o m p l e t e d   o n   2 0 2 6 - 1 1 - 0 2   1 4 : 5 9 : 0 3  
 m y s q l d u m p   :   m y s q l d u m p :   [ W a r n i n g ]   U s i n g   a   p a s s w o r d   o n   t h e   c o m m a n d   l i n e   i n t e r f a c e   c a n   b e   i n s e c u r e .  
 E n   l í n e a :   1   C a r á c t e r :   1  
 +   m y s q l d u m p   - u   r o o t   - p r o o t   p s y a i _ c o n n e c t   R e g i s t e r   s o c i a l a c c o u n t _ s o c i a l a   . . .  
 +   ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~  
         +   C a t e g o r y I n f o                     :   N o t S p e c i f i e d :   ( m y s q l d u m p :   [ W a r . . . a n   b e   i n s e c u r e . : S t r i n g )   [ ] ,   R e m o t e E x c e p t i o n  
         +   F u l l y Q u a l i f i e d E r r o r I d   :   N a t i v e C o m m a n d E r r o r  
    
 - -   M y S Q L   d u m p   1 0 . 1 3     D i s t r i b   8 . 0 . 4 6 ,   f o r   W i n 6 4   ( x 8 6 _ 6 4 )  
 - -  
 - -   H o s t :   l o c a l h o s t         D a t a b a s e :   p s y a i _ c o n n e c t  
 - -   - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  
 - -   S e r v e r   v e r s i o n 	 8 . 0 . 4 6  
  
 / * ! 4 0 1 0 1   S E T   @ O L D _ C H A R A C T E R _ S E T _ C L I E N T = @ @ C H A R A C T E R _ S E T _ C L I E N T   * / ;  
 / * ! 4 0 1 0 1   S E T   @ O L D _ C H A R A C T E R _ S E T _ R E S U L T S = @ @ C H A R A C T E R _ S E T _ R E S U L T S   * / ;  
 / * ! 4 0 1 0 1   S E T   @ O L D _ C O L L A T I O N _ C O N N E C T I O N = @ @ C O L L A T I O N _ C O N N E C T I O N   * / ;  
 / * ! 5 0 5 0 3   S E T   N A M E S   u t f 8 m b 4   * / ;  
 / * ! 4 0 1 0 3   S E T   @ O L D _ T I M E _ Z O N E = @ @ T I M E _ Z O N E   * / ;  
 / * ! 4 0 1 0 3   S E T   T I M E _ Z O N E = ' + 0 0 : 0 0 '   * / ;  
 / * ! 4 0 0 1 4   S E T   @ O L D _ U N I Q U E _ C H E C K S = @ @ U N I Q U E _ C H E C K S ,   U N I Q U E _ C H E C K S = 0   * / ;  
 / * ! 4 0 0 1 4   S E T   @ O L D _ F O R E I G N _ K E Y _ C H E C K S = @ @ F O R E I G N _ K E Y _ C H E C K S ,   F O R E I G N _ K E Y _ C H E C K S = 0   * / ;  
 / * ! 4 0 1 0 1   S E T   @ O L D _ S Q L _ M O D E = @ @ S Q L _ M O D E ,   S Q L _ M O D E = ' N O _ A U T O _ V A L U E _ O N _ Z E R O '   * / ;  
 / * ! 4 0 1 1 1   S E T   @ O L D _ S Q L _ N O T E S = @ @ S Q L _ N O T E S ,   S Q L _ N O T E S = 0   * / ;  
  
 - -  
 - -   T a b l e   s t r u c t u r e   f o r   t a b l e   ` r e g i s t e r `  
 - -  
  
 D R O P   T A B L E   I F   E X I S T S   ` r e g i s t e r ` ;  
 / * ! 4 0 1 0 1   S E T   @ s a v e d _ c s _ c l i e n t           =   @ @ c h a r a c t e r _ s e t _ c l i e n t   * / ;  
 / * ! 5 0 5 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   u t f 8 m b 4   * / ;  
 C R E A T E   T A B L E   ` r e g i s t e r `   (  
     ` i d U s u a r i o `   i n t   N O T   N U L L   A U T O _ I N C R E M E N T ,  
     ` n o m b r e `   v a r c h a r ( 1 2 0 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` e m a i l `   v a r c h a r ( 1 2 0 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` c o n t r a s e n a `   v a r c h a r ( 2 5 5 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` r o l `   e n u m ( ' p a c i e n t e ' , ' p r o f e s i o n a l ' , ' a d m i n ' )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   N O T   N U L L ,  
     ` f o t o P e r f i l `   v a r c h a r ( 2 5 5 )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   D E F A U L T   N U L L ,  
     ` e s t a d o C u e n t a `   e n u m ( ' A c t i v a ' , ' S u s p e n d i d a ' )   C O L L A T E   u t f 8 m b 4 _ u n i c o d e _ c i   D E F A U L T   ' A c t i v a ' ,  
     ` a c t i v o `   t i n y i n t ( 1 )   N O T   N U L L   D E F A U L T   ' 1 ' ,  
     ` f e c h a R e g i s t r o `   d a t e t i m e   D E F A U L T   C U R R E N T _ T I M E S T A M P ,  
     ` l a s t _ l o g i n `   d a t e t i m e ( 6 )   D E F A U L T   N U L L ,  
     ` e m a i l _ v e r i f i c a d o `   t i n y i n t ( 1 )   N O T   N U L L ,  
     P R I M A R Y   K E Y   ( ` i d U s u a r i o ` ) ,  
     U N I Q U E   K E Y   ` e m a i l `   ( ` e m a i l ` )  
 )   E N G I N E = I n n o D B   A U T O _ I N C R E M E N T = 3 5   D E F A U L T   C H A R S E T = u t f 8 m b 4   C O L L A T E = u t f 8 m b 4 _ u n i c o d e _ c i ;  
 / * ! 4 0 1 0 1   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   @ s a v e d _ c s _ c l i e n t   * / ;  
  
 - -  
 - -   D u m p i n g   d a t a   f o r   t a b l e   ` r e g i s t e r `  
 - -  
  
 L O C K   T A B L E S   ` r e g i s t e r `   W R I T E ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` r e g i s t e r `   D I S A B L E   K E Y S   * / ;  
 I N S E R T   I N T O   ` r e g i s t e r `   V A L U E S   ( 1 , ' A d m i n i s t r a d o r ' , ' a d m i n @ p s y a i . c o m ' , ' 6 0 f e 7 4 4 0 6 e 7 f 3 5 3 e d 9 7 9 f 3 5 0 f 2 f b b 6 a 2 e 8 6 9 0 a 5 f a 7 d 1 b 0 c 3 2 9 8 3 d 1 d 8 b 3 f 9 5 f 6 7 ' , ' a d m i n ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 5   1 6 : 1 6 : 1 9 ' , N U L L , 0 ) , ( 2 , ' M a n u e l ' , ' p a c i e n t e @ g m a i l . c o m ' , ' $ 2 b $ 1 2 $ o I J d x x 1 G x p F Z L . H K E c O 7 M u d F 4 t x p A x q F 4 k S e a y K r S x . I 3 F O f y G s W y ' , ' p r o f e s i o n a l ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 7   1 2 : 5 3 : 3 2 ' , N U L L , 0 ) , ( 3 , ' P r o f e s i o n a l ' , ' p r o f e s i o n a l @ p s y a i . c o m ' , ' 7 8 2 0 9 2 4 a d a b b c c 8 b e a c e 4 9 a 9 4 9 8 b 8 a e d 5 1 0 d f 4 2 7 8 0 4 c f 7 a 9 3 d 2 4 3 4 1 a b 7 d a a a 1 1 ' , ' p r o f e s i o n a l ' , ' 1 6 a 8 7 1 a 5 3 3 2 c 4 c 4 2 b 6 b a 4 8 b 1 3 4 9 d 3 7 8 0 . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 7   1 8 : 0 0 : 2 8 ' , ' 2 0 2 6 - 1 0 - 2 7   0 2 : 4 2 : 4 4 . 9 6 5 0 1 7 ' , 0 ) , ( 4 , ' A d m i n 2 ' , ' a d m i n 2 @ p s y a i . c o m ' , ' 2 4 0 b e 5 1 8 f a b d 2 7 2 4 d d b 6 f 0 4 e e b 1 d a 5 9 6 7 4 4 8 d 7 e 8 3 1 c 0 8 c 8 f a 8 2 2 8 0 9 f 7 4 c 7 2 0 a 9 ' , ' a d m i n ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 0 7   1 8 : 0 0 : 2 8 ' , ' 2 0 2 6 - 1 0 - 2 9   0 4 : 1 0 : 3 2 . 4 7 5 7 7 2 ' , 0 ) , ( 5 , ' M a n u e l 2 ' , ' p a c i e n t e 2 @ g m a i l . c o m ' , ' 2 9 9 f b b 4 5 5 c 4 2 2 3 9 c 8 6 d 2 e e 3 b 1 5 4 0 3 e d 1 b 4 6 8 2 5 9 e c a e d f 0 c 3 5 2 7 4 5 1 e 1 f 0 d 6 3 d 5 9 ' , ' p a c i e n t e ' , ' 0 e 0 6 a 3 0 f c 7 a d 4 4 3 7 9 b b a 7 9 b e b 2 d e 3 b f 6 . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 1 6   2 3 : 0 0 : 1 2 ' , N U L L , 0 ) , ( 6 , ' t e s t ' , ' t e s t @ g m a i l . c o m ' , ' $ 2 b $ 1 2 $ F 9 4 l e F E v c 0 h p h 7 N 1 O 8 v x 5 u P X v p 7 . q v B q f o t o u Z g d S a V R f i 7 Y t y g w C ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 6 - 1 6   2 3 : 1 4 : 3 7 ' , N U L L , 0 ) , ( 8 , ' M a n u e l ' , ' m a n @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , ' e a b d 7 a 0 e c 6 3 6 4 9 4 3 a 0 5 a f 5 8 d b 2 5 b 9 b e 5 . p n g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 0 3   0 1 : 5 0 : 1 6 ' , N U L L , 0 ) , ( 1 0 , ' M a n u e l ' , ' t e s t 3 @ g m a i l . c o m ' , ' 8 d 9 6 9 e e f 6 e c a d 3 c 2 9 a 3 a 6 2 9 2 8 0 e 6 8 6 c f 0 c 3 f 5 d 5 a 8 6 a f f 3 c a 1 2 0 2 0 c 9 2 3 a d c 6 c 9 2 ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 1 2   0 1 : 3 0 : 3 6 ' , ' 2 0 2 6 - 1 0 - 2 7   0 5 : 3 8 : 0 5 . 4 1 5 6 1 1 ' , 0 ) , ( 1 1 , ' h o l a ' , ' h o l a @ g m a i l . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 1 2   0 3 : 1 3 : 3 7 ' , N U L L , 0 ) , ( 1 2 , ' t e s t ' , ' p a c i e n t e 3 @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , ' 6 3 8 9 4 d c f b d c 8 4 6 2 4 a 8 7 d f a 0 6 6 8 f a 4 1 5 e . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 1 2   0 3 : 3 6 : 1 8 ' , ' 2 0 2 6 - 0 9 - 2 5   0 5 : 0 1 : 3 5 . 7 7 5 5 7 3 ' , 0 ) , ( 1 4 , ' M a n u e l   R o j a s ' , ' m a n u e l r o j a s q 2 1 @ g m a i l . c o m ' , ' 6 4 1 a e 3 5 4 f 6 0 6 4 e c c b 8 7 3 f 2 7 4 4 8 b 0 d c 3 b ' , ' p a c i e n t e ' , ' ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 1 4 : 4 6 ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 1 4 : 4 6 . 1 9 7 1 4 0 ' , 0 ) , ( 1 5 , ' L e g e n d a r y G h o u l   W l ' , ' m a n o l o r o j a s 2 6 1 0 2 0 0 2 @ g m a i l . c o m ' , ' 5 7 f 8 1 7 1 9 a c a 8 4 d 1 5 8 5 2 5 1 6 9 d 3 2 6 9 3 1 a d ' , ' p a c i e n t e ' , ' ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 1 8 : 2 8 ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 3 6 : 4 0 . 2 3 4 9 3 8 ' , 0 ) , ( 1 6 , ' M a n u e l   R o j a s ' , ' m a n u e l a l e j a n d r o . r o j a s q u i n t e r o @ g m a i l . c o m ' , ' 8 6 7 f 2 7 6 c 4 7 1 8 4 b 7 0 a 1 1 8 d 7 4 4 2 1 d e e c 6 0 ' , ' p a c i e n t e ' , ' c 0 9 a 1 4 d f d c 2 4 4 1 d d a 6 d 2 b 6 f e 3 7 0 a d 6 0 a . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 1 : 1 6 ' , ' 2 0 2 6 - 0 8 - 0 5   0 3 : 2 6 : 2 1 . 4 6 5 0 1 0 ' , 0 ) , ( 1 7 , ' L e g e n d   P l u s   Ò â ä ' , ' m a n u e l r o j a s q u i n t e r o 7 0 0 @ g m a i l . c o m ' , ' 4 9 7 1 d a c 3 8 f f 0 4 b c c 9 5 a 3 8 7 4 4 a 2 7 4 5 1 0 b ' , ' p a c i e n t e ' , ' h t t p s : / / l h 3 . g o o g l e u s e r c o n t e n t . c o m / a / A C g 8 o c I 5 E 3 u o i X 1 7 l y x H Q p T 0 3 U y k 5 B 3 j D 9 G w P v H 8 0 m T _ 1 M d s B e k p E k F 9 = s 9 6 - c ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 9 : 0 5 ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 9 : 0 4 . 6 4 8 6 8 5 ' , 0 ) , ( 1 8 , ' M a n u e l 2 ' , ' c u e n t a i n v e n t a d a @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 8 - 0 4   0 2 : 2 5 : 0 1 ' , N U L L , 0 ) , ( 1 9 , ' M a n u e l ' , ' r a n d o m @ g m a i l . c o m ' , ' e b 6 8 e d 1 d 7 d f e e 9 c 5 9 d c 5 8 2 b 0 0 7 5 3 9 1 1 2 3 2 8 2 3 f 0 8 e a c 7 0 8 2 5 8 5 e a 1 e 2 0 e a f 7 6 d e e ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 1 8   2 3 : 0 3 : 1 9 ' , N U L L , 0 ) , ( 2 0 , ' H o l a   H O L A ' , ' m a n u e l a l e j a n d r o . r o j a s q u i n t e r o 3 @ g m a i l . c o m ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ o G 1 K t m w u N C H j J P P z N 0 W V q 3 $ 6 M g D 4 f F 6 Y f O P F H e + F c M 8 5 C H h 1 P f x P E 6 f h s + M h v c r I G 4 = ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 2 2   0 7 : 0 1 : 1 3 ' , N U L L , 0 ) , ( 2 3 , ' n e p e   n e p e ' , ' a a a @ g m a i l . c o m ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ m J q k O C k e i q F s e q o q S t R 0 Q X $ N J K G s 7 Z u H y 1 s k Q U Z D n V M b Q o F k m J 8 q Q + P M 7 B T w w h 9 N Y A = ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 2 3   1 7 : 0 8 : 5 9 ' , N U L L , 0 ) , ( 2 8 , ' M a n u e l 3 3 3 ' , ' t e s t e o @ g m a i l . c o m ' , ' a r g o n 2 $ a r g o n 2 i d $ v = 1 9 $ m = 1 0 2 4 0 0 , t = 2 , p = 8 $ N k Z y Y 1 F m c 2 1 P M F A 0 W F B P T 1 F 1 M E w x c g $ M K Q S F W 0 d s O V z N D S Y n g m 5 y f M E 7 c y b 6 8 2 i q E V w I p y 2 Q F U ' , ' p a c i e n t e ' , ' b 8 d 4 5 a 1 a 2 4 2 6 4 2 e a 9 0 2 8 0 0 b d 9 2 2 f 7 b 9 d . j p g ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 0 9 - 2 5   0 6 : 0 3 : 5 6 ' , ' 2 0 2 6 - 1 0 - 3 0   0 5 : 0 9 : 3 7 . 4 9 1 1 9 4 ' , 1 ) , ( 2 9 , ' T e s t   C h a t ' , ' t e s t c h a t @ t e s t . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 0 5 : 1 8 ' , N U L L , 0 ) , ( 3 0 , ' T e s t   U s e r ' , ' t e s t 1 2 3 @ t e s t . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 3 6 : 1 9 ' , N U L L , 0 ) , ( 3 1 , ' T e s t 4 5 6 ' , ' t e s t 4 5 6 @ t e s t . c o m ' , ' ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 3 6 : 4 7 ' , N U L L , 0 ) , ( 3 2 , ' T e s t 7 8 9 ' , ' t e s t 7 8 9 @ t e s t . c o m ' , ' b d 9 4 d c d a 2 6 f c c b 4 e 6 8 d 6 a 3 1 f 9 b 5 a a c 0 b 5 7 1 a e 2 6 6 d 8 2 2 6 2 0 e 9 0 1 e f 7 e b e 3 a 1 1 d 4 f ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 3 7 : 0 9 ' , ' 2 0 2 6 - 1 0 - 2 6   0 5 : 4 5 : 4 3 . 4 2 9 0 1 0 ' , 0 ) , ( 3 3 , ' s s   s s ' , ' t e s t e o 2 @ g m a i l . c o m ' , ' p b k d f 2 _ s h a 2 5 6 $ 1 0 0 0 0 0 0 $ 5 8 e l T 7 9 m 2 L i U f 0 b n v m i 6 M h $ m y d Q b 9 C I b g p v 1 M z U q Y 7 d E A n Y / Q M u K P e G c H k O f 8 c S S 9 U = ' , ' p a c i e n t e ' , N U L L , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 0 - 2 7   0 6 : 3 7 : 1 4 ' , N U L L , 0 ) , ( 3 4 , ' B r a y a n ' , ' h i p e r b r a y a n 1 4 @ g m a i l . c o m ' , ' a r g o n 2 $ a r g o n 2 i d $ v = 1 9 $ m = 1 0 2 4 0 0 , t = 2 , p = 8 $ c X o 3 d z d S a V V s U T V 0 S H h P Q X Z Q e G d i N g $ x J O K b H / h G O S Q h S J 3 p t 8 0 H 6 E t P t 2 + N 9 5 u t M d H K 6 Q C w c M ' , ' p a c i e n t e ' , ' h t t p s : / / l h 3 . g o o g l e u s e r c o n t e n t . c o m / a / A C g 8 o c L 2 m u g G h X 9 F h y N J 1 1 1 A J C o Z m d f A 5 s M 3 B k B D t k Q t D E L m q l M p b w = s 9 6 - c ' , ' A c t i v a ' , 1 , ' 2 0 2 6 - 1 1 - 0 2   2 0 : 0 1 : 5 7 ' , N U L L , 0 ) ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` r e g i s t e r `   E N A B L E   K E Y S   * / ;  
 U N L O C K   T A B L E S ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ c s _ c l i e n t             =   @ @ c h a r a c t e r _ s e t _ c l i e n t   * /   ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ c s _ r e s u l t s           =   @ @ c h a r a c t e r _ s e t _ r e s u l t s   * /   ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ c o l _ c o n n e c t i o n   =   @ @ c o l l a t i o n _ c o n n e c t i o n   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t     =   u t f 8 m b 4   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ r e s u l t s   =   u t f 8 m b 4   * /   ;  
 / * ! 5 0 0 0 3   S E T   c o l l a t i o n _ c o n n e c t i o n     =   u t f 8 m b 4 _ 0 9 0 0 _ a i _ c i   * /   ;  
 / * ! 5 0 0 0 3   S E T   @ s a v e d _ s q l _ m o d e               =   @ @ s q l _ m o d e   * /   ;  
 / * ! 5 0 0 0 3   S E T   s q l _ m o d e                             =   ' N O _ A U T O _ V A L U E _ O N _ Z E R O '   * /   ;  
 D E L I M I T E R   ; ;  
 / * ! 5 0 0 0 3   C R E A T E * /   / * ! 5 0 0 1 7   D E F I N E R = ` r o o t ` @ ` l o c a l h o s t ` * /   / * ! 5 0 0 0 3   T R I G G E R   ` t r g _ r e g i s t r a r _ r e a c t i v a c i o n `   A F T E R   U P D A T E   O N   ` r e g i s t e r `   F O R   E A C H   R O W   B E G I N  
         I F   N E W . e s t a d o C u e n t a   =   ' A c t i v a '   A N D   O L D . e s t a d o C u e n t a   =   ' S u s p e n d i d a '   T H E N  
                 I N S E R T   I N T O   A u d i t o r i a A c c e s o s   ( i d U s u a r i o ,   a c c i o n ,   i p )  
                 V A L U E S   ( N E W . i d U s u a r i o ,   ' R e a c t i v a c i %%n   d e   c u e n t a ' ,   ' 0 . 0 . 0 . 0 ' ) ;  
         E N D   I F ;  
 E N D   * / ; ;  
 D E L I M I T E R   ;  
 / * ! 5 0 0 0 3   S E T   s q l _ m o d e                             =   @ s a v e d _ s q l _ m o d e   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t     =   @ s a v e d _ c s _ c l i e n t   * /   ;  
 / * ! 5 0 0 0 3   S E T   c h a r a c t e r _ s e t _ r e s u l t s   =   @ s a v e d _ c s _ r e s u l t s   * /   ;  
 / * ! 5 0 0 0 3   S E T   c o l l a t i o n _ c o n n e c t i o n     =   @ s a v e d _ c o l _ c o n n e c t i o n   * /   ;  
  
 - -  
 - -   T a b l e   s t r u c t u r e   f o r   t a b l e   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `  
 - -  
  
 D R O P   T A B L E   I F   E X I S T S   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t ` ;  
 / * ! 4 0 1 0 1   S E T   @ s a v e d _ c s _ c l i e n t           =   @ @ c h a r a c t e r _ s e t _ c l i e n t   * / ;  
 / * ! 5 0 5 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   u t f 8 m b 4   * / ;  
 C R E A T E   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `   (  
     ` i d `   i n t   N O T   N U L L   A U T O _ I N C R E M E N T ,  
     ` p r o v i d e r `   v a r c h a r ( 2 0 0 )   N O T   N U L L ,  
     ` u i d `   v a r c h a r ( 1 9 1 )   N O T   N U L L ,  
     ` l a s t _ l o g i n `   d a t e t i m e ( 6 )   N O T   N U L L ,  
     ` d a t e _ j o i n e d `   d a t e t i m e ( 6 )   N O T   N U L L ,  
     ` e x t r a _ d a t a `   j s o n   N O T   N U L L ,  
     ` u s e r _ i d `   i n t   N O T   N U L L ,  
     P R I M A R Y   K E Y   ( ` i d ` ) ,  
     U N I Q U E   K E Y   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t _ p r o v i d e r _ u i d _ f c 8 1 0 c 6 e _ u n i q `   ( ` p r o v i d e r ` , ` u i d ` ) ,  
     K E Y   ` s o c i a l a c c o u n t _ s o c i a l _ u s e r _ i d _ 8 1 4 6 e 7 0 c _ f k _ R e g i s t e r _ `   ( ` u s e r _ i d ` ) ,  
     C O N S T R A I N T   ` s o c i a l a c c o u n t _ s o c i a l _ u s e r _ i d _ 8 1 4 6 e 7 0 c _ f k _ R e g i s t e r _ `   F O R E I G N   K E Y   ( ` u s e r _ i d ` )   R E F E R E N C E S   ` r e g i s t e r `   ( ` i d U s u a r i o ` )  
 )   E N G I N E = I n n o D B   A U T O _ I N C R E M E N T = 7   D E F A U L T   C H A R S E T = u t f 8 m b 4   C O L L A T E = u t f 8 m b 4 _ 0 9 0 0 _ a i _ c i ;  
 / * ! 4 0 1 0 1   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   @ s a v e d _ c s _ c l i e n t   * / ;  
  
 - -  
 - -   D u m p i n g   d a t a   f o r   t a b l e   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `  
 - -  
  
 L O C K   T A B L E S   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `   W R I T E ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `   D I S A B L E   K E Y S   * / ;  
 I N S E R T   I N T O   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `   V A L U E S   ( 5 , ' g o o g l e ' , ' 1 1 6 7 7 3 6 9 8 3 7 9 5 9 5 2 8 9 5 8 4 ' , ' 2 0 2 6 - 0 8 - 0 5   0 3 : 2 6 : 2 1 . 4 5 2 8 5 6 ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 1 : 1 6 . 1 8 3 0 6 6 ' , ' { \ " a u d \ " :   \ " 2 0 7 0 5 0 9 8 8 1 1 4 - 7 s r q 2 s 5 u t p 0 0 i r 9 g m m k b n a j r 4 g 4 i t a 2 3 . a p p s . g o o g l e u s e r c o n t e n t . c o m \ " ,   \ " a z p \ " :   \ " 2 0 7 0 5 0 9 8 8 1 1 4 - 7 s r q 2 s 5 u t p 0 0 i r 9 g m m k b n a j r 4 g 4 i t a 2 3 . a p p s . g o o g l e u s e r c o n t e n t . c o m \ " ,   \ " e x p \ " :   1 7 8 5 9 0 3 9 8 2 ,   \ " i a t \ " :   1 7 8 5 9 0 0 3 8 2 ,   \ " i s s \ " :   \ " h t t p s : / / a c c o u n t s . g o o g l e . c o m \ " ,   \ " s u b \ " :   \ " 1 1 6 7 7 3 6 9 8 3 7 9 5 9 5 2 8 9 5 8 4 \ " ,   \ " n a m e \ " :   \ " M a n u e l   R o j a s \ " ,   \ " e m a i l \ " :   \ " m a n u e l a l e j a n d r o . r o j a s q u i n t e r o @ g m a i l . c o m \ " ,   \ " a t _ h a s h \ " :   \ " H Q U z q y c H Z m W q S 8 X f F W 0 w d w \ " ,   \ " p i c t u r e \ " :   \ " h t t p s : / / l h 3 . g o o g l e u s e r c o n t e n t . c o m / a / A C g 8 o c K q i o s l C S P O t B I Q j L 8 H J E o 7 J y k p r C Z K A C L J I p Y o 4 v Q I w J I s Y e M = s 9 6 - c \ " ,   \ " g i v e n _ n a m e \ " :   \ " M a n u e l \ " ,   \ " f a m i l y _ n a m e \ " :   \ " R o j a s \ " ,   \ " e m a i l _ v e r i f i e d \ " :   t r u e } ' , 1 6 ) , ( 6 , ' g o o g l e ' , ' 1 0 6 5 6 2 7 7 6 2 5 7 4 2 8 4 8 8 6 2 7 ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 9 : 0 4 . 6 3 8 4 9 7 ' , ' 2 0 2 6 - 0 7 - 3 1   2 0 : 5 9 : 0 4 . 6 3 8 5 1 2 ' , ' { \ " a u d \ " :   \ " 2 0 7 0 5 0 9 8 8 1 1 4 - 7 s r q 2 s 5 u t p 0 0 i r 9 g m m k b n a j r 4 g 4 i t a 2 3 . a p p s . g o o g l e u s e r c o n t e n t . c o m \ " ,   \ " a z p \ " :   \ " 2 0 7 0 5 0 9 8 8 1 1 4 - 7 s r q 2 s 5 u t p 0 0 i r 9 g m m k b n a j r 4 g 4 i t a 2 3 . a p p s . g o o g l e u s e r c o n t e n t . c o m \ " ,   \ " e x p \ " :   1 7 8 5 5 3 5 1 4 4 ,   \ " i a t \ " :   1 7 8 5 5 3 1 5 4 4 ,   \ " i s s \ " :   \ " h t t p s : / / a c c o u n t s . g o o g l e . c o m \ " ,   \ " s u b \ " :   \ " 1 0 6 5 6 2 7 7 6 2 5 7 4 2 8 4 8 8 6 2 7 \ " ,   \ " n a m e \ " :   \ " L e g e n d   P l u s   Ò â ä \ " ,   \ " e m a i l \ " :   \ " m a n u e l r o j a s q u i n t e r o 7 0 0 @ g m a i l . c o m \ " ,   \ " a t _ h a s h \ " :   \ " W d A p J W e L R K 4 J g Q Y X n d r G r w \ " ,   \ " p i c t u r e \ " :   \ " h t t p s : / / l h 3 . g o o g l e u s e r c o n t e n t . c o m / a / A C g 8 o c I 5 E 3 u o i X 1 7 l y x H Q p T 0 3 U y k 5 B 3 j D 9 G w P v H 8 0 m T _ 1 M d s B e k p E k F 9 = s 9 6 - c \ " ,   \ " g i v e n _ n a m e \ " :   \ " L e g e n d \ " ,   \ " f a m i l y _ n a m e \ " :   \ " P l u s   Ò â ä \ " ,   \ " e m a i l _ v e r i f i e d \ " :   t r u e } ' , 1 7 ) ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `   E N A B L E   K E Y S   * / ;  
 U N L O C K   T A B L E S ;  
  
 - -  
 - -   T a b l e   s t r u c t u r e   f o r   t a b l e   ` s o c i a l a c c o u n t _ s o c i a l a p p `  
 - -  
  
 D R O P   T A B L E   I F   E X I S T S   ` s o c i a l a c c o u n t _ s o c i a l a p p ` ;  
 / * ! 4 0 1 0 1   S E T   @ s a v e d _ c s _ c l i e n t           =   @ @ c h a r a c t e r _ s e t _ c l i e n t   * / ;  
 / * ! 5 0 5 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   u t f 8 m b 4   * / ;  
 C R E A T E   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l a p p `   (  
     ` i d `   i n t   N O T   N U L L   A U T O _ I N C R E M E N T ,  
     ` p r o v i d e r `   v a r c h a r ( 3 0 )   N O T   N U L L ,  
     ` n a m e `   v a r c h a r ( 4 0 )   N O T   N U L L ,  
     ` c l i e n t _ i d `   v a r c h a r ( 1 9 1 )   N O T   N U L L ,  
     ` s e c r e t `   v a r c h a r ( 1 9 1 )   N O T   N U L L ,  
     ` k e y `   v a r c h a r ( 1 9 1 )   N O T   N U L L ,  
     ` p r o v i d e r _ i d `   v a r c h a r ( 2 0 0 )   N O T   N U L L ,  
     ` s e t t i n g s `   j s o n   N O T   N U L L   D E F A U L T   ( _ u t f 8 m b 4 ' { } ' ) ,  
     P R I M A R Y   K E Y   ( ` i d ` )  
 )   E N G I N E = I n n o D B   A U T O _ I N C R E M E N T = 2   D E F A U L T   C H A R S E T = u t f 8 m b 4   C O L L A T E = u t f 8 m b 4 _ 0 9 0 0 _ a i _ c i ;  
 / * ! 4 0 1 0 1   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   @ s a v e d _ c s _ c l i e n t   * / ;  
  
 - -  
 - -   D u m p i n g   d a t a   f o r   t a b l e   ` s o c i a l a c c o u n t _ s o c i a l a p p `  
 - -  
  
 L O C K   T A B L E S   ` s o c i a l a c c o u n t _ s o c i a l a p p `   W R I T E ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l a p p `   D I S A B L E   K E Y S   * / ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l a p p `   E N A B L E   K E Y S   * / ;  
 U N L O C K   T A B L E S ;  
  
 - -  
 - -   T a b l e   s t r u c t u r e   f o r   t a b l e   ` s o c i a l a c c o u n t _ s o c i a l t o k e n `  
 - -  
  
 D R O P   T A B L E   I F   E X I S T S   ` s o c i a l a c c o u n t _ s o c i a l t o k e n ` ;  
 / * ! 4 0 1 0 1   S E T   @ s a v e d _ c s _ c l i e n t           =   @ @ c h a r a c t e r _ s e t _ c l i e n t   * / ;  
 / * ! 5 0 5 0 3   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   u t f 8 m b 4   * / ;  
 C R E A T E   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l t o k e n `   (  
     ` i d `   i n t   N O T   N U L L   A U T O _ I N C R E M E N T ,  
     ` t o k e n `   l o n g t e x t   N O T   N U L L ,  
     ` t o k e n _ s e c r e t `   l o n g t e x t   N O T   N U L L ,  
     ` e x p i r e s _ a t `   d a t e t i m e ( 6 )   D E F A U L T   N U L L ,  
     ` a c c o u n t _ i d `   i n t   N O T   N U L L ,  
     ` a p p _ i d `   i n t   D E F A U L T   N U L L ,  
     P R I M A R Y   K E Y   ( ` i d ` ) ,  
     U N I Q U E   K E Y   ` s o c i a l a c c o u n t _ s o c i a l t o k e n _ a p p _ i d _ a c c o u n t _ i d _ f c a 4 e 0 a c _ u n i q `   ( ` a p p _ i d ` , ` a c c o u n t _ i d ` ) ,  
     K E Y   ` s o c i a l a c c o u n t _ s o c i a l _ a c c o u n t _ i d _ 9 5 1 f 2 1 0 e _ f k _ s o c i a l a c c `   ( ` a c c o u n t _ i d ` ) ,  
     C O N S T R A I N T   ` s o c i a l a c c o u n t _ s o c i a l _ a c c o u n t _ i d _ 9 5 1 f 2 1 0 e _ f k _ s o c i a l a c c `   F O R E I G N   K E Y   ( ` a c c o u n t _ i d ` )   R E F E R E N C E S   ` s o c i a l a c c o u n t _ s o c i a l a c c o u n t `   ( ` i d ` ) ,  
     C O N S T R A I N T   ` s o c i a l a c c o u n t _ s o c i a l _ a p p _ i d _ 6 3 6 a 4 2 d 7 _ f k _ s o c i a l a c c `   F O R E I G N   K E Y   ( ` a p p _ i d ` )   R E F E R E N C E S   ` s o c i a l a c c o u n t _ s o c i a l a p p `   ( ` i d ` )  
 )   E N G I N E = I n n o D B   D E F A U L T   C H A R S E T = u t f 8 m b 4   C O L L A T E = u t f 8 m b 4 _ 0 9 0 0 _ a i _ c i ;  
 / * ! 4 0 1 0 1   S E T   c h a r a c t e r _ s e t _ c l i e n t   =   @ s a v e d _ c s _ c l i e n t   * / ;  
  
 - -  
 - -   D u m p i n g   d a t a   f o r   t a b l e   ` s o c i a l a c c o u n t _ s o c i a l t o k e n `  
 - -  
  
 L O C K   T A B L E S   ` s o c i a l a c c o u n t _ s o c i a l t o k e n `   W R I T E ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l t o k e n `   D I S A B L E   K E Y S   * / ;  
 / * ! 4 0 0 0 0   A L T E R   T A B L E   ` s o c i a l a c c o u n t _ s o c i a l t o k e n `   E N A B L E   K E Y S   * / ;  
 U N L O C K   T A B L E S ;  
 / * ! 4 0 1 0 3   S E T   T I M E _ Z O N E = @ O L D _ T I M E _ Z O N E   * / ;  
  
 / * ! 4 0 1 0 1   S E T   S Q L _ M O D E = @ O L D _ S Q L _ M O D E   * / ;  
 / * ! 4 0 0 1 4   S E T   F O R E I G N _ K E Y _ C H E C K S = @ O L D _ F O R E I G N _ K E Y _ C H E C K S   * / ;  
 / * ! 4 0 0 1 4   S E T   U N I Q U E _ C H E C K S = @ O L D _ U N I Q U E _ C H E C K S   * / ;  
 / * ! 4 0 1 0 1   S E T   C H A R A C T E R _ S E T _ C L I E N T = @ O L D _ C H A R A C T E R _ S E T _ C L I E N T   * / ;  
 / * ! 4 0 1 0 1   S E T   C H A R A C T E R _ S E T _ R E S U L T S = @ O L D _ C H A R A C T E R _ S E T _ R E S U L T S   * / ;  
 / * ! 4 0 1 0 1   S E T   C O L L A T I O N _ C O N N E C T I O N = @ O L D _ C O L L A T I O N _ C O N N E C T I O N   * / ;  
 / * ! 4 0 1 1 1   S E T   S Q L _ N O T E S = @ O L D _ S Q L _ N O T E S   * / ;  
  
 - -   D u m p   c o m p l e t e d   o n   2 0 2 6 - 1 1 - 0 2   1 5 : 0 3 : 3 1  
 