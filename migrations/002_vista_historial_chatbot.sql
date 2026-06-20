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
INNER JOIN Register r ON c.idPaciente = r.idUsuario;
