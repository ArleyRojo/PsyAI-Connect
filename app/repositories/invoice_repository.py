# ============================================================
# ARCHIVO: repositories/invoice_repository.py
# ============================================================

from app.utils.db import db_cursor


def create_invoice(patient_id, professional_id, cita_id, items, metodo_pago):
    with db_cursor(dictionary=True) as (conn, cursor):
        try:
            monto = sum(item["precioUnitario"] for item in items)
            cursor.execute(
                """
                INSERT INTO Facturas
                    (idPaciente, idProfesional, idCita, monto, metodoPago, estadoPago)
                VALUES (%s, %s, %s, %s, %s, 'Pendiente')
                """,
                (patient_id, professional_id, cita_id, monto, metodo_pago),
            )
            invoice_id = cursor.lastrowid

            for item in items:
                cursor.execute(
                    """
                    INSERT INTO ItemsFactura (idFactura, descripcion, precioUnitario)
                    VALUES (%s, %s, %s)
                    """,
                    (invoice_id, item["descripcion"], item["precioUnitario"]),
                )
            conn.commit()
            return invoice_id
        except Exception:
            conn.rollback()
            raise


def get_invoice_by_id(invoice_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT f.*, p.nombre AS nombrePaciente,
                   pr.nombre AS nombreProfesional
            FROM Facturas f
            JOIN Register p ON f.idPaciente = p.idUsuario
            JOIN Register pr ON f.idProfesional = pr.idUsuario
            WHERE f.idFactura = %s
            """,
            (invoice_id,),
        )
        factura = cursor.fetchone()
        if not factura:
            return None
        cursor.execute(
            "SELECT * FROM ItemsFactura WHERE idFactura = %s",
            (invoice_id,),
        )
        factura["items"] = cursor.fetchall()
        return factura


def list_invoices_by_patient(patient_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT f.*, pr.nombre AS nombreProfesional
            FROM Facturas f
            JOIN Register pr ON f.idProfesional = pr.idUsuario
            WHERE f.idPaciente = %s
            ORDER BY f.fecha DESC
            """,
            (patient_id,),
        )
        facturas = cursor.fetchall()
        for factura in facturas:
            cursor.execute(
                "SELECT * FROM ItemsFactura WHERE idFactura = %s",
                (factura["idFactura"],),
            )
            factura["items"] = cursor.fetchall()
        return facturas


def list_invoices_by_professional(professional_id, estado=None, fecha_desde=None, fecha_hasta=None):
    conditions = ["f.idProfesional = %s"]
    params = [professional_id]

    if estado:
        if estado == "Anulada":
            conditions.append("f.anulada = 1")
        else:
            conditions.append("f.anulada = 0 AND f.estadoPago = %s")
            params.append(estado)

    if fecha_desde:
        conditions.append("f.fecha >= %s")
        params.append(fecha_desde)
    if fecha_hasta:
        conditions.append("f.fecha < %s")
        params.append(fecha_hasta + " 23:59:59")

    sql = f"""
        SELECT f.*, p.nombre AS nombrePaciente
        FROM Facturas f
        JOIN Register p ON f.idPaciente = p.idUsuario
        WHERE {' AND '.join(conditions)}
        ORDER BY f.fecha DESC
    """
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(sql, tuple(params))
        facturas = cursor.fetchall()
        for factura in facturas:
            cursor.execute(
                "SELECT * FROM ItemsFactura WHERE idFactura = %s",
                (factura["idFactura"],),
            )
            factura["items"] = cursor.fetchall()
        return facturas


def list_all_invoices(paciente=None, profesional=None, estado=None, metodo_pago=None, fecha_desde=None, fecha_hasta=None):
    conditions = []
    params = []

    if paciente:
        conditions.append("p.nombre LIKE %s")
        params.append(f"%{paciente}%")
    if profesional:
        conditions.append("pr.nombre LIKE %s")
        params.append(f"%{profesional}%")
    if estado:
        if estado == "Anulada":
            conditions.append("f.anulada = 1")
        else:
            conditions.append("f.anulada = 0 AND f.estadoPago = %s")
            params.append(estado)
    if metodo_pago:
        conditions.append("f.metodoPago = %s")
        params.append(metodo_pago)
    if fecha_desde:
        conditions.append("f.fecha >= %s")
        params.append(fecha_desde)
    if fecha_hasta:
        conditions.append("f.fecha < %s")
        params.append(fecha_hasta + " 23:59:59")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            f"""
            SELECT f.*, p.nombre AS nombrePaciente, pr.nombre AS nombreProfesional
            FROM Facturas f
            JOIN Register p ON f.idPaciente = p.idUsuario
            JOIN Register pr ON f.idProfesional = pr.idUsuario
            WHERE {where_clause}
            ORDER BY f.fecha DESC
            """,
            tuple(params),
        )
        facturas = cursor.fetchall()
        for factura in facturas:
            cursor.execute(
                "SELECT * FROM ItemsFactura WHERE idFactura = %s",
                (factura["idFactura"],),
            )
            factura["items"] = cursor.fetchall()
        return facturas


def update_payment_status(invoice_id, nuevo_estado):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE Facturas SET estadoPago = %s WHERE idFactura = %s",
            (nuevo_estado, invoice_id),
        )
        conn.commit()
        return cursor.rowcount


def annul_invoice(invoice_id, motivo):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE Facturas SET anulada = 1, motivoAnulacion = %s WHERE idFactura = %s",
            (motivo, invoice_id),
        )
        conn.commit()
        return cursor.rowcount


def set_payment_reference(invoice_id, referencia, id_transaccion):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE Facturas SET referenciaPago = %s, idTransaccionPago = %s WHERE idFactura = %s",
            (referencia, id_transaccion, invoice_id),
        )
        conn.commit()
        return cursor.rowcount


def get_invoice_by_reference(reference):
    with db_cursor() as (_, cursor):
        cursor.execute(
            "SELECT idFactura FROM Facturas WHERE referenciaPago = %s",
            (reference,),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def get_invoice_owner(invoice_id):
    with db_cursor() as (_, cursor):
        cursor.execute(
            "SELECT idPaciente, idProfesional, anulada FROM Facturas WHERE idFactura = %s",
            (invoice_id,),
        )
        return cursor.fetchone()


def get_professional_patients(professional_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT DISTINCT r.idUsuario, r.nombre
            FROM PacientesProfesional pp
            JOIN Register r ON pp.idPaciente = r.idUsuario
            WHERE pp.idProfesional = %s
            ORDER BY r.nombre
            """,
            (professional_id,),
        )
        return cursor.fetchall()


def get_invoice_stats_by_professional(professional_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN f.anulada = 0 AND f.estadoPago = 'Pagado' THEN f.monto ELSE 0 END), 0) AS totalPagado,
                COALESCE(SUM(CASE WHEN f.anulada = 0 AND f.estadoPago IN ('Pendiente','Parcial') THEN f.monto ELSE 0 END), 0) AS totalPendiente,
                COALESCE(SUM(CASE WHEN f.anulada = 0 THEN f.monto ELSE 0 END), 0) AS totalGeneral
            FROM Facturas f
            WHERE f.idProfesional = %s
            """,
            (professional_id,),
        )
        return cursor.fetchone()


def get_invoice_stats_all():
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN f.anulada = 0 THEN f.monto ELSE 0 END), 0) AS totalFacturado,
                COALESCE(SUM(CASE WHEN f.anulada = 0 AND f.estadoPago = 'Pagado' THEN f.monto ELSE 0 END), 0) AS totalPagado,
                COALESCE(SUM(CASE WHEN f.anulada = 0 AND f.estadoPago IN ('Pendiente','Parcial') THEN f.monto ELSE 0 END), 0) AS totalPendiente,
                COALESCE(SUM(f.anulada), 0) AS anuladas
            FROM Facturas f
            """,
        )
        return cursor.fetchone()
