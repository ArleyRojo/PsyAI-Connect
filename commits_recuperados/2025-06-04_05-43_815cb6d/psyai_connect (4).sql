-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 27-04-2026 a las 21:47:40
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

CREATE DATABASE psyai_connect;
USE psyai_connect;
--
-- Base de datos: `psyai_connect`
--

DELIMITER $$
--
-- Procedimientos
--
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_AgendarCita` (IN `p_paciente` INT, IN `p_profesional` INT, IN `p_fecha` DATE, IN `p_hora` TIME, IN `p_tipoCita` VARCHAR(80), IN `p_tipoSesion` VARCHAR(80), IN `p_motivo` TEXT, IN `p_notas` TEXT)   BEGIN
  INSERT INTO Citas(idPaciente, idProfesional, fecha, hora, tipoCita, tipoSesion, motivo, notas)
  VALUES (p_paciente, p_profesional, p_fecha, p_hora, p_tipoCita, p_tipoSesion, p_motivo, p_notas);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_CrearFactura` (IN `p_paciente` INT, IN `p_profesional` INT, IN `p_cita` INT, IN `p_monto` DECIMAL(10,2), IN `p_metodoPago` VARCHAR(20))   BEGIN
  INSERT INTO Facturas(idPaciente, idProfesional, idCita, monto, metodoPago)
  VALUES (p_paciente, p_profesional, p_cita, p_monto, p_metodoPago);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_GenerarReporte` (IN `p_profesional` INT, IN `p_paciente` INT, IN `p_tipo` VARCHAR(80), IN `p_fechaInicio` DATE, IN `p_fechaFin` DATE)   BEGIN
  INSERT INTO Reportes(idProfesional, idPaciente, tipoReporte, fechaInicio, fechaFin)
  VALUES (p_profesional, p_paciente, p_tipo, p_fechaInicio, p_fechaFin);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_Login` (IN `p_email` VARCHAR(120), IN `p_contra` VARCHAR(200))   BEGIN
  SELECT idUsuario, nombre, email, rol, estadoCuenta
  FROM Register
  WHERE email       = p_email
    AND contrasena  = p_contra
    AND estadoCuenta = 'Activa';
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_Register` (IN `p_nombre` VARCHAR(120), IN `p_email` VARCHAR(120), IN `p_contra` VARCHAR(200), IN `p_rol` VARCHAR(20))   BEGIN
  INSERT INTO Register(nombre, email, contrasena, rol)
  VALUES (p_nombre, p_email, p_contra, p_rol);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_RegistrarEvolucion` (IN `p_paciente` INT, IN `p_estadoEmocional` VARCHAR(100), IN `p_nivelEnergia` INT, IN `p_notas` TEXT)   BEGIN
  INSERT INTO EvolucionPaciente(idPaciente, estadoEmocional, nivelEnergia, notasPersonales)
  VALUES (p_paciente, p_estadoEmocional, p_nivelEnergia, p_notas);
END$$

DELIMITER ;

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

--
-- Volcado de datos para la tabla `auditoriaaccesos`
--

INSERT INTO `auditoriaaccesos` (`idAuditoria`, `idUsuario`, `accion`, `ip`, `fecha`) VALUES
(1, 5, 'Login exitoso', '127.0.0.1', '2026-04-24 13:31:17'),
(2, 4, 'Login exitoso', '127.0.0.1', '2026-04-24 13:32:01'),
(3, 5, 'Login exitoso', '127.0.0.1', '2026-04-24 13:38:37'),
(4, 5, 'Login exitoso', '127.0.0.1', '2026-04-24 13:46:58'),
(5, 7, 'Login exitoso', '127.0.0.1', '2026-04-24 16:39:40'),
(6, 2, 'Login exitoso', '127.0.0.1', '2026-04-24 16:41:43'),
(7, 6, 'Login exitoso', '127.0.0.1', '2026-04-24 16:42:57'),
(8, 2, 'Login exitoso', '127.0.0.1', '2026-04-24 16:46:36'),
(9, 4, 'Login exitoso', '127.0.0.1', '2026-04-24 17:18:54'),
(10, 2, 'Login exitoso', '127.0.0.1', '2026-04-24 17:24:08'),
(11, 5, 'Login exitoso', '127.0.0.1', '2026-04-24 17:26:16'),
(12, 4, 'Reactivación de cuenta', '0.0.0.0', '2026-04-24 17:27:04'),
(13, 4, 'Login exitoso', '127.0.0.1', '2026-04-27 13:36:55'),
(14, 2, 'Login exitoso', '127.0.0.1', '2026-04-27 13:40:11'),
(15, 4, 'Login exitoso', '127.0.0.1', '2026-04-27 13:41:31'),
(16, 2, 'Login exitoso', '127.0.0.1', '2026-04-27 13:48:06'),
(17, 4, 'Login exitoso', '127.0.0.1', '2026-04-27 14:01:24'),
(18, 2, 'Login exitoso', '127.0.0.1', '2026-04-27 14:02:44');

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

--
-- Volcado de datos para la tabla `citas`
--

INSERT INTO `citas` (`idCita`, `idPaciente`, `idProfesional`, `fecha`, `hora`, `tipoCita`, `tipoSesion`, `motivo`, `notas`, `estado`) VALUES
(1, 4, 2, '2026-03-24', '12:30:00', 'Depresión', NULL, 'Quiero conversar', NULL, 'Pendiente'),
(2, 4, 2, '2026-03-26', '17:00:00', 'Seguimiento', NULL, 'Seguimiento del paciente', NULL, 'Pendiente'),
(3, 4, 2, '2026-03-30', '10:00:00', 'Estrés', NULL, 'Quiero hablar', NULL, 'Pendiente'),
(4, 4, 2, '2026-04-28', '08:00:00', 'Ansiedad', NULL, 'jujnj', NULL, 'Pendiente');

--
-- Disparadores `citas`
--
DELIMITER $$
CREATE TRIGGER `trg_cita_notificacion_paciente` AFTER INSERT ON `citas` FOR EACH ROW BEGIN
  INSERT INTO Notificaciones (idUsuario, titulo, mensaje, tipo, estado, enviado_por)
  VALUES (NEW.idPaciente, 'Nueva cita', 'Se ha programado una nueva cita.', 'Cita', 'enviado', 'Sistema');
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `trg_cita_notificacion_profesional` AFTER INSERT ON `citas` FOR EACH ROW BEGIN
  INSERT INTO Notificaciones (idUsuario, titulo, mensaje, tipo, estado, enviado_por)
  VALUES (NEW.idProfesional, 'Nueva cita agendada', 'Tienes una nueva cita agendada.', 'Cita', 'enviado', 'Sistema');
END
$$
DELIMITER ;

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


CREATE TABLE `ChatHistorial` (
  `idMensaje` int(11) NOT NULL AUTO_INCREMENT,
  `idPaciente` int(11) NOT NULL,
  `tipo` varchar(10) NOT NULL COMMENT 'usuario o bot',
  `mensaje` text NOT NULL,
  `fecha` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`idMensaje`),
  KEY `idx_chathistorial_paciente` (`idPaciente`),
  CONSTRAINT `chathistorial_ibfk_1` FOREIGN KEY (`idPaciente`)
    REFERENCES `register` (`idUsuario`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Disparadores `conversacioneschatbot`
--
DELIMITER $$
CREATE TRIGGER `trg_alerta_emocional` AFTER INSERT ON `conversacioneschatbot` FOR EACH ROW BEGIN
  IF NEW.nivelEmocionalDetectado = 'Alto' THEN
    INSERT INTO Notificaciones (idUsuario, mensaje, tipo, estado)
    VALUES (
      NEW.idPaciente,
      'Se detectó un estado emocional crítico. Un profesional revisará tu caso.',
      'Alerta',
      'enviado'
    );
  END IF;
END
$$
DELIMITER ;

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

--
-- Volcado de datos para la tabla `disponibilidad`
--

INSERT INTO `disponibilidad` (`idDisponibilidad`, `idProfesional`, `fecha`, `hora_inicio`, `hora_fin`, `estado`) VALUES
(1, 2, '2026-03-24', '12:30:00', '13:30:00', 'Disponible'),
(2, 2, '2026-03-26', '16:00:00', '20:00:00', 'Disponible'),
(3, 2, '2026-03-30', '08:00:00', '14:00:00', 'Disponible'),
(4, 2, '2026-04-24', '08:00:00', '08:30:00', 'Disponible'),
(5, 2, '2026-04-24', '09:30:00', '10:00:00', 'Disponible'),
(6, 2, '2026-04-24', '10:30:00', '11:00:00', 'Disponible'),
(7, 2, '2026-04-24', '14:00:00', '14:30:00', 'Disponible'),
(8, 2, '2026-04-28', '08:00:00', '08:30:00', 'Disponible');

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

--
-- Disparadores `evolucionpaciente`
--
DELIMITER $$
CREATE TRIGGER `trg_evolucion_notificacion` AFTER INSERT ON `evolucionpaciente` FOR EACH ROW BEGIN
  INSERT INTO Notificaciones (idUsuario, titulo, mensaje, tipo, estado, enviado_por)
  VALUES (NEW.idPaciente, 'Evolución registrada', 'Se ha registrado tu nueva evolución emocional.', 'Evolución', 'enviado', 'Sistema');
END
$$
DELIMITER ;

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

--
-- Disparadores `facturas`
--
DELIMITER $$
CREATE TRIGGER `trg_evitar_factura_duplicada` BEFORE INSERT ON `facturas` FOR EACH ROW BEGIN
  IF EXISTS (
    SELECT 1 FROM Facturas
    WHERE idPaciente = NEW.idPaciente
      AND DATE(fecha) = CURDATE()
      AND idCita      = NEW.idCita
  ) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Ya existe una factura para esta cita hoy.';
  END IF;
END
$$
DELIMITER ;

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

--
-- Volcado de datos para la tabla `login`
--

INSERT INTO `login` (`idLogin`, `idUsuario`, `email`, `contrasena`, `ultimoAcceso`) VALUES
(1, 2, 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', '2026-03-21 01:03:36'),
(2, 2, 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', '2026-03-21 01:35:57'),
(3, 2, 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', '2026-03-21 01:50:17'),
(4, 2, 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', '2026-03-21 01:57:38'),
(5, 4, 'Arleyandresrojomarin07@gmail.com', '88c1dfce34f5a1b4508a341be5a2ff6f97f9d2ef75ddb9b0ffb60c5073f3ae10', '2026-03-21 02:13:16'),
(6, 4, 'Arleyandresrojomarin07@gmail.com', '88c1dfce34f5a1b4508a341be5a2ff6f97f9d2ef75ddb9b0ffb60c5073f3ae10', '2026-03-21 02:17:42'),
(7, 4, 'Arleyandresrojomarin07@gmail.com', '88c1dfce34f5a1b4508a341be5a2ff6f97f9d2ef75ddb9b0ffb60c5073f3ae10', '2026-03-21 02:24:25'),
(8, 4, 'Arleyandresrojomarin07@gmail.com', '88c1dfce34f5a1b4508a341be5a2ff6f97f9d2ef75ddb9b0ffb60c5073f3ae10', '2026-03-21 02:33:11'),
(9, 4, 'Arleyandresrojomarin07@gmail.com', '88c1dfce34f5a1b4508a341be5a2ff6f97f9d2ef75ddb9b0ffb60c5073f3ae10', '2026-03-21 12:23:39'),
(10, 2, 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', '2026-03-21 12:26:13'),
(11, 2, 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', '2026-03-21 12:36:23'),
(12, 4, 'Arleyandresrojomarin07@gmail.com', '88c1dfce34f5a1b4508a341be5a2ff6f97f9d2ef75ddb9b0ffb60c5073f3ae10', '2026-03-21 12:46:18'),
(13, 2, 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', '2026-03-21 12:51:14'),
(14, 5, 'arleyadmin@psyai.com', '', '2026-04-24 13:31:17'),
(15, 4, 'arleyandresrojomarin07@gmail.com', '', '2026-04-24 13:32:01'),
(16, 5, 'arleyadmin@psyai.com', '', '2026-04-24 13:38:37'),
(17, 5, 'arleyadmin@psyai.com', '', '2026-04-24 13:46:58'),
(18, 7, 'arleypaciente@psyai.com', '', '2026-04-24 16:39:40'),
(19, 2, 'rojoarleymarinandres07@gmail.com', '', '2026-04-24 16:41:43'),
(20, 6, 'arleyprofesional@psyai.com', '', '2026-04-24 16:42:57'),
(21, 2, 'rojoarleymarinandres07@gmail.com', '', '2026-04-24 16:46:36'),
(22, 4, 'arleyandresrojomarin07@gmail.com', '', '2026-04-24 17:18:54'),
(23, 2, 'rojoarleymarinandres07@gmail.com', '', '2026-04-24 17:24:08'),
(24, 5, 'arleyadmin@psyai.com', '', '2026-04-24 17:26:16'),
(25, 4, 'arleyandresrojomarin07@gmail.com', '', '2026-04-27 13:36:55'),
(26, 2, 'rojoarleymarinandres07@gmail.com', '', '2026-04-27 13:40:11'),
(27, 4, 'arleyandresrojomarin07@gmail.com', '', '2026-04-27 13:41:31'),
(28, 2, 'rojoarleymarinandres07@gmail.com', '', '2026-04-27 13:48:06'),
(29, 4, 'arleyandresrojomarin07@gmail.com', '', '2026-04-27 14:01:24'),
(30, 2, 'rojoarleymarinandres07@gmail.com', '', '2026-04-27 14:02:44');

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
  `rol_anterior` varchar(20) DEFAULT NULL,
  `rol_nuevo` varchar(20) DEFAULT NULL,
  `usuario_afectado` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `logs`
--

INSERT INTO `logs` (`idLog`, `administrador`, `modulo`, `accion`, `detalle`, `fecha`, `rol_anterior`, `rol_nuevo`, `usuario_afectado`) VALUES
(1, 'Arley Admin', 'usuarios', 'Suspender usuario', 'Suspendido: Arley Rojo', '2026-04-24 17:26:53', NULL, NULL, NULL),
(2, 'Arley Admin', 'usuarios', 'Reestablecer usuario', 'Reestablecido: Arley Rojo', '2026-04-24 17:27:04', NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `notificaciones`
--

CREATE TABLE `notificaciones` (
  `idNotificacion` int(11) NOT NULL,
  `idUsuario` int(11) DEFAULT NULL,
  `rol` enum('admin','profesional','paciente') DEFAULT NULL,
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

--
-- Volcado de datos para la tabla `notificaciones`
--

INSERT INTO `notificaciones` (`idNotificacion`, `idUsuario`, `titulo`, `mensaje`, `tipo`, `destinatario`, `email_individual`, `enviado_por`, `estado`, `leido`, `fecha`, `fecha_programada`) VALUES
(1, 4, 'Nueva cita', 'Se ha programado una nueva cita.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-24 18:15:07', NULL),
(2, 2, 'Nueva cita agendada', 'Tienes una nueva cita agendada.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-24 18:15:07', NULL),
(3, 4, 'Nueva cita', 'Se ha programado una nueva cita.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-24 18:15:07', NULL),
(4, 2, 'Nueva cita agendada', 'Tienes una nueva cita agendada.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-24 18:15:07', NULL),
(5, 4, 'Nueva cita', 'Se ha programado una nueva cita.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-24 18:15:07', NULL),
(6, 2, 'Nueva cita agendada', 'Tienes una nueva cita agendada.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-24 18:15:07', NULL),
(7, 4, 'Nueva cita', 'Se ha programado una nueva cita.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-27 13:47:35', NULL),
(8, 2, 'Nueva cita agendada', 'Tienes una nueva cita agendada.', 'Cita', NULL, NULL, 'Sistema', 'enviado', 0, '2026-04-27 13:47:35', NULL);

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

--
-- Volcado de datos para la tabla `perfilpaciente`
--

INSERT INTO `perfilpaciente` (`idPaciente`, `edad`, `genero`, `numeroTelefonico`, `consentimientoDatos`) VALUES
(4, NULL, 'Masculino', NULL, 0);

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

--
-- Volcado de datos para la tabla `perfilprofesional`
--

INSERT INTO `perfilprofesional` (`idProfesional`, `especialidad`, `licencia`, `experiencia`, `estado`) VALUES
(2, NULL, NULL, NULL, 'Activo');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `recoverytokens`
--

CREATE TABLE `recoverytokens` (
  `idToken` int(11) NOT NULL,
  `idUsuario` int(11) NOT NULL,
  `token` varchar(100) NOT NULL,
  `expires` datetime NOT NULL,
  `used` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

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

--
-- Volcado de datos para la tabla `register`
--

INSERT INTO `register` (`idUsuario`, `nombre`, `email`, `contrasena`, `rol`, `fotoPerfil`, `estadoCuenta`, `activo`, `fechaRegistro`) VALUES
(1, 'Administrador', 'admin@psyai.com', '60fe74406e7f353ed979f350f2fbb6a2e8690a5fa7d1b0c32983d1d8b3f95f67', 'admin', NULL, 'Activa', 1, '2026-03-21 00:08:39'),
(2, 'Andres Marin', 'rojoarleymarinandres07@gmail.com', '5a06bbcaee7dfaa12c3f5fb5e7550facc52a099c8ab83baff4aba281f91831df', 'profesional', NULL, 'Activa', 1, '2026-03-21 01:03:06'),
(4, 'Arley Rojo', 'Arleyandresrojomarin07@gmail.com', '88c1dfce34f5a1b4508a341be5a2ff6f97f9d2ef75ddb9b0ffb60c5073f3ae10', 'paciente', NULL, 'Activa', 1, '2026-03-21 02:12:47'),
(5, 'Arley Admin', 'arleyadmin@psyai.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin', NULL, 'Activa', 1, '2026-04-24 18:27:47'),
(6, 'Arley Profesional', 'arleyprofesional@psyai.com', 'cb1513ece93b4a593042a5c181ab2e123260f197a51a92b758c1697839067669', 'profesional', NULL, 'Activa', 1, '2026-04-24 18:27:47'),
(7, 'Arley Paciente', 'arleypaciente@psyai.com', '299fbb455c42239c86d2ee3b15403ed1b468259ecaedf0c3527451e1f0d63d59', 'paciente', NULL, 'Activa', 1, '2026-04-24 18:27:47');

--
-- Disparadores `register`
--
DELIMITER $$
CREATE TRIGGER `trg_registrar_reactivacion` AFTER UPDATE ON `register` FOR EACH ROW BEGIN
  IF NEW.estadoCuenta = 'Activa' AND OLD.estadoCuenta = 'Suspendida' THEN
    INSERT INTO AuditoriaAccesos (idUsuario, accion, ip)
    VALUES (NEW.idUsuario, 'Reactivación de cuenta', '0.0.0.0');
  END IF;
END
$$
DELIMITER ;

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
  `fecha` datetime DEFAULT current_timestamp(),
  `eliminado` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `reportes`
--

INSERT INTO `reportes` (`idReporte`, `idProfesional`, `idPaciente`, `tipoReporte`, `fechaInicio`, `fechaFin`, `estado`, `fecha`, `eliminado`) VALUES
(1, 6, 4, 'diagnosticos', '2026-04-24', '2026-04-25', 'Completado', '2026-04-24 16:43:21', 1),
(2, 2, 4, 'diagnosticos', '2026-04-27', '2026-04-28', 'Completado', '2026-04-27 14:34:31', 1);

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vistacitaspendientes`
-- (Véase abajo para la vista actual)
--
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

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vistaevolucionpaciente`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `vistaevolucionpaciente` (
`nombre` varchar(120)
,`estadoEmocional` varchar(100)
,`nivelEnergia` int(11)
,`notasPersonales` text
,`fecha` datetime
);

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vistafacturacion`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `vistafacturacion` (
`idFactura` int(11)
,`paciente` varchar(120)
,`monto` decimal(10,2)
,`metodoPago` enum('banco','tarjeta')
,`estadoPago` enum('Pendiente','Pagado')
,`fecha` datetime
);

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vistahistorialchatbot`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `vistahistorialchatbot` (
`nombre` varchar(120)
,`mensajeUsuario` text
,`respuestaChatbot` text
,`nivelEmocionalDetectado` varchar(50)
,`fecha` datetime
);

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vistalogsadmin`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `vistalogsadmin` (
`id` int(11)
,`administrador` varchar(120)
,`modulo` varchar(80)
,`accion` varchar(120)
,`detalle` mediumtext
,`fecha` varchar(21)
,`origen` varchar(9)
);

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vistareportes`
-- (Véase abajo para la vista actual)
--
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

--
-- Estructura para la vista `vistacitaspendientes`
--
DROP TABLE IF EXISTS `vistacitaspendientes`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistacitaspendientes`  AS SELECT `c`.`idCita` AS `idCita`, `u`.`nombre` AS `paciente`, `c`.`fecha` AS `fecha`, `c`.`hora` AS `hora`, `c`.`tipoCita` AS `tipoCita`, `c`.`tipoSesion` AS `tipoSesion`, `c`.`motivo` AS `motivo`, `c`.`notas` AS `notas`, `c`.`estado` AS `estado` FROM (`citas` `c` join `register` `u` on(`c`.`idPaciente` = `u`.`idUsuario`)) WHERE `c`.`estado` = 'Pendiente' ;

-- --------------------------------------------------------

--
-- Estructura para la vista `vistaevolucionpaciente`
--
DROP TABLE IF EXISTS `vistaevolucionpaciente`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistaevolucionpaciente`  AS SELECT `u`.`nombre` AS `nombre`, `e`.`estadoEmocional` AS `estadoEmocional`, `e`.`nivelEnergia` AS `nivelEnergia`, `e`.`notasPersonales` AS `notasPersonales`, `e`.`fecha` AS `fecha` FROM (`evolucionpaciente` `e` join `register` `u` on(`e`.`idPaciente` = `u`.`idUsuario`)) ;

-- --------------------------------------------------------

--
-- Estructura para la vista `vistafacturacion`
--
DROP TABLE IF EXISTS `vistafacturacion`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistafacturacion`  AS SELECT `f`.`idFactura` AS `idFactura`, `u`.`nombre` AS `paciente`, `f`.`monto` AS `monto`, `f`.`metodoPago` AS `metodoPago`, `f`.`estadoPago` AS `estadoPago`, `f`.`fecha` AS `fecha` FROM (`facturas` `f` join `register` `u` on(`f`.`idPaciente` = `u`.`idUsuario`)) ;

-- --------------------------------------------------------

--
-- Estructura para la vista `vistahistorialchatbot`
--
DROP TABLE IF EXISTS `vistahistorialchatbot`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistahistorialchatbot`  AS SELECT `u`.`nombre` AS `nombre`, `c`.`mensajeUsuario` AS `mensajeUsuario`, `c`.`respuestaChatbot` AS `respuestaChatbot`, `c`.`nivelEmocionalDetectado` AS `nivelEmocionalDetectado`, `c`.`fecha` AS `fecha` FROM (`conversacioneschatbot` `c` join `register` `u` on(`c`.`idPaciente` = `u`.`idUsuario`)) ;

-- --------------------------------------------------------

--
-- Estructura para la vista `vistalogsadmin`
--
DROP TABLE IF EXISTS `vistalogsadmin`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistalogsadmin`  AS SELECT `l`.`idLog` AS `id`, `l`.`administrador` AS `administrador`, `l`.`modulo` AS `modulo`, `l`.`accion` AS `accion`, `l`.`detalle` AS `detalle`, date_format(`l`.`fecha`,'%d/%m/%Y %H:%i') AS `fecha`, 'admin' AS `origen` FROM `logs` AS `l`union all select `a`.`idAuditoria` AS `id`,coalesce(`r`.`nombre`,concat('Usuario #',`a`.`idUsuario`)) AS `administrador`,'accesos' AS `modulo`,`a`.`accion` AS `accion`,concat('IP: ',`a`.`ip`) AS `detalle`,date_format(`a`.`fecha`,'%d/%m/%Y %H:%i') AS `fecha`,'auditoria' AS `origen` from (`auditoriaaccesos` `a` left join `register` `r` on(`a`.`idUsuario` = `r`.`idUsuario`))  ;

-- --------------------------------------------------------

--
-- Estructura para la vista `vistareportes`
--
DROP TABLE IF EXISTS `vistareportes`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vistareportes`  AS SELECT `r`.`idReporte` AS `idReporte`, `up`.`nombre` AS `profesional`, `ua`.`nombre` AS `paciente`, `r`.`tipoReporte` AS `tipoReporte`, `r`.`fechaInicio` AS `fechaInicio`, `r`.`fechaFin` AS `fechaFin`, `r`.`estado` AS `estado`, `r`.`fecha` AS `fecha` FROM ((`reportes` `r` join `register` `up` on(`r`.`idProfesional` = `up`.`idUsuario`)) left join `register` `ua` on(`r`.`idPaciente` = `ua`.`idUsuario`)) ;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `auditoriaaccesos`
--
ALTER TABLE `auditoriaaccesos`
  ADD PRIMARY KEY (`idAuditoria`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Indices de la tabla `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`idCita`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idProfesional` (`idProfesional`);

--
-- Indices de la tabla `conversacioneschatbot`
--
ALTER TABLE `conversacioneschatbot`
  ADD PRIMARY KEY (`idConversacion`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- Indices de la tabla `disponibilidad`
--
ALTER TABLE `disponibilidad`
  ADD PRIMARY KEY (`idDisponibilidad`),
  ADD KEY `idProfesional` (`idProfesional`);

--
-- Indices de la tabla `evolucionpaciente`
--
ALTER TABLE `evolucionpaciente`
  ADD PRIMARY KEY (`idEvolucion`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idConversacion` (`idConversacion`);

--
-- Indices de la tabla `facturas`
--
ALTER TABLE `facturas`
  ADD PRIMARY KEY (`idFactura`),
  ADD KEY `idPaciente` (`idPaciente`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idCita` (`idCita`);

--
-- Indices de la tabla `itemsfactura`
--
ALTER TABLE `itemsfactura`
  ADD PRIMARY KEY (`idItem`),
  ADD KEY `idFactura` (`idFactura`);

--
-- Indices de la tabla `login`
--
ALTER TABLE `login`
  ADD PRIMARY KEY (`idLogin`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Indices de la tabla `logs`
--
ALTER TABLE `logs`
  ADD PRIMARY KEY (`idLog`);

--
-- Indices de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  ADD PRIMARY KEY (`idNotificacion`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Indices de la tabla `pacientesprofesional`
--
ALTER TABLE `pacientesprofesional`
  ADD PRIMARY KEY (`idRegistro`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- Indices de la tabla `perfilpaciente`
--
ALTER TABLE `perfilpaciente`
  ADD PRIMARY KEY (`idPaciente`);

--
-- Indices de la tabla `perfilprofesional`
--
ALTER TABLE `perfilprofesional`
  ADD PRIMARY KEY (`idProfesional`);

--
-- Indices de la tabla `recoverytokens`
--
ALTER TABLE `recoverytokens`
  ADD PRIMARY KEY (`idToken`),
  ADD UNIQUE KEY `token` (`token`),
  ADD KEY `idUsuario` (`idUsuario`);

--
-- Indices de la tabla `register`
--
ALTER TABLE `register`
  ADD PRIMARY KEY (`idUsuario`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indices de la tabla `reportes`
--
ALTER TABLE `reportes`
  ADD PRIMARY KEY (`idReporte`),
  ADD KEY `idProfesional` (`idProfesional`),
  ADD KEY `idPaciente` (`idPaciente`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `auditoriaaccesos`
--
ALTER TABLE `auditoriaaccesos`
  MODIFY `idAuditoria` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT de la tabla `citas`
--
ALTER TABLE `citas`
  MODIFY `idCita` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `conversacioneschatbot`
--
ALTER TABLE `conversacioneschatbot`
  MODIFY `idConversacion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `disponibilidad`
--
ALTER TABLE `disponibilidad`
  MODIFY `idDisponibilidad` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT de la tabla `evolucionpaciente`
--
ALTER TABLE `evolucionpaciente`
  MODIFY `idEvolucion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `facturas`
--
ALTER TABLE `facturas`
  MODIFY `idFactura` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `itemsfactura`
--
ALTER TABLE `itemsfactura`
  MODIFY `idItem` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `login`
--
ALTER TABLE `login`
  MODIFY `idLogin` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=31;

--
-- AUTO_INCREMENT de la tabla `logs`
--
ALTER TABLE `logs`
  MODIFY `idLog` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  MODIFY `idNotificacion` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT de la tabla `pacientesprofesional`
--
ALTER TABLE `pacientesprofesional`
  MODIFY `idRegistro` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `recoverytokens`
--
ALTER TABLE `recoverytokens`
  MODIFY `idToken` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `register`
--
ALTER TABLE `register`
  MODIFY `idUsuario` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de la tabla `reportes`
--
ALTER TABLE `reportes`
  MODIFY `idReporte` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `auditoriaaccesos`
--
ALTER TABLE `auditoriaaccesos`
  ADD CONSTRAINT `auditoriaaccesos_ibfk_1` FOREIGN KEY (`idUsuario`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `citas`
--
ALTER TABLE `citas`
  ADD CONSTRAINT `citas_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `citas_ibfk_2` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `conversacioneschatbot`
--
ALTER TABLE `conversacioneschatbot`
  ADD CONSTRAINT `conversacioneschatbot_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `disponibilidad`
--
ALTER TABLE `disponibilidad`
  ADD CONSTRAINT `disponibilidad_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `evolucionpaciente`
--
ALTER TABLE `evolucionpaciente`
  ADD CONSTRAINT `evolucionpaciente_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `evolucionpaciente_ibfk_2` FOREIGN KEY (`idConversacion`) REFERENCES `conversacioneschatbot` (`idConversacion`) ON DELETE SET NULL;

--
-- Filtros para la tabla `facturas`
--
ALTER TABLE `facturas`
  ADD CONSTRAINT `facturas_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `facturas_ibfk_2` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `facturas_ibfk_3` FOREIGN KEY (`idCita`) REFERENCES `citas` (`idCita`) ON DELETE SET NULL;

--
-- Filtros para la tabla `itemsfactura`
--
ALTER TABLE `itemsfactura`
  ADD CONSTRAINT `itemsfactura_ibfk_1` FOREIGN KEY (`idFactura`) REFERENCES `facturas` (`idFactura`) ON DELETE CASCADE;

--
-- Filtros para la tabla `login`
--
ALTER TABLE `login`
  ADD CONSTRAINT `login_ibfk_1` FOREIGN KEY (`idUsuario`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  ADD CONSTRAINT `notificaciones_ibfk_1` FOREIGN KEY (`idUsuario`) REFERENCES `register` (`idUsuario`) ON DELETE SET NULL;

--
-- Filtros para la tabla `pacientesprofesional`
--
ALTER TABLE `pacientesprofesional`
  ADD CONSTRAINT `pacientesprofesional_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `pacientesprofesional_ibfk_2` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE SET NULL;

--
-- Filtros para la tabla `perfilpaciente`
--
ALTER TABLE `perfilpaciente`
  ADD CONSTRAINT `perfilpaciente_ibfk_1` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `perfilprofesional`
--
ALTER TABLE `perfilprofesional`
  ADD CONSTRAINT `perfilprofesional_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `recoverytokens`
--
ALTER TABLE `recoverytokens`
  ADD CONSTRAINT `recoverytokens_ibfk_1` FOREIGN KEY (`idUsuario`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `reportes`
--
ALTER TABLE `reportes`
  ADD CONSTRAINT `reportes_ibfk_1` FOREIGN KEY (`idProfesional`) REFERENCES `register` (`idUsuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `reportes_ibfk_2` FOREIGN KEY (`idPaciente`) REFERENCES `register` (`idUsuario`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

-- ============================================================
-- Crear usuario admin con contrasena NULL en register
-- Base de datos: psyai_connect
-- ============================================================

USE `psyai_connect`;

-- Paso 1: Permitir NULL en la columna contrasena (es NOT NULL por defecto)
ALTER TABLE `register`
  MODIFY COLUMN `contrasena` VARCHAR(200) DEFAULT NULL;

-- Paso 2: Insertar admin con contrasena NULL
INSERT INTO `register`
  (`nombre`, `email`, `contrasena`, `rol`, `fotoPerfil`, `estadoCuenta`, `activo`)
VALUES
  ('Admin', 'admintest@psyai.com', NULL, 'admin', NULL, 'Activa', 1);

-- Paso 3: Verificar inserción
SELECT `idUsuario`, `nombre`, `email`, `contrasena`, `rol`, `estadoCuenta`
FROM `register`
WHERE `rol` = 'admin';

INSERT INTO `register` (`nombre`, `email`, `contrasena`, `rol`, `estadoCuenta`, `activo`)
VALUES ('Admin', 'admincasa@psyai.com', SHA2('admin123', 256), 'admin', 'Activa', 1);

INSERT INTO `register` 
  (`nombre`, `email`, `contrasena`, `rol`, `estadoCuenta`, `activo`)
VALUES (
  'Admin',
  'admintest2@psyai.com',
  SHA2('tu_contraseña_aqui', 256),
  'admin',
  'Activa',
  1
);

INSERT INTO `register` 
  (`idUsuario`, `nombre`, `email`, `contrasena`, `rol`, `estadoCuenta`, `activo`)
VALUES (
  24,
  'Admin',
  'admin24@psyai.com',
  SHA2('admin123', 256),
  'admin',
  'Activa',
  1
);

INSERT INTO `register` 
  (`idUsuario`, `nombre`, `email`, `contrasena`, `rol`, `estadoCuenta`, `activo`)
VALUES 
  (25, 'Admin Nuevo', 'admin25@psyai.com', SHA2('admin123', 256), 'admin', 'Activa', 1),
  (26, 'Profesional Nuevo', 'profesional26@psyai.com', SHA2('prof123', 256), 'profesional', 'Activa', 1);

-- Crear perfil profesional para el ID 26 (obligatorio por la FK)
INSERT INTO `PerfilProfesional` (`idProfesional`)
VALUES (26);

SELECT * FROM register;

-- ============================================================
-- Tablas ChatbotConfig y ChatHistorial (faltantes en esquema)
-- ============================================================

CREATE TABLE `ChatbotConfig` (
  `id` int(11) NOT NULL DEFAULT 1,
  `system_prompt` text DEFAULT NULL,
  `risk_terms` text DEFAULT NULL,
  `crisis_response` text DEFAULT NULL,
  `fallback_response` text DEFAULT NULL,
  `temperature` decimal(3,2) DEFAULT 0.55,
  `top_p` decimal(3,2) DEFAULT 0.90,
  `max_tokens` int(11) DEFAULT 420,
  `actualizado_por` int(11) DEFAULT NULL,
  `fecha_actualizacion` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `chatbotconfig_ibfk_1` FOREIGN KEY (`actualizado_por`)
    REFERENCES `register` (`idUsuario`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `ChatHistorial` (
  `idMensaje` int(11) NOT NULL AUTO_INCREMENT,
  `idPaciente` int(11) NOT NULL,
  `tipo` varchar(10) NOT NULL COMMENT 'usuario o bot',
  `mensaje` text NOT NULL,
  `fecha` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`idMensaje`),
  KEY `idx_chathistorial_paciente` (`idPaciente`),
  CONSTRAINT `chathistorial_ibfk_1` FOREIGN KEY (`idPaciente`)
    REFERENCES `register` (`idUsuario`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;