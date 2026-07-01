# ============================================================
# ARCHIVO: repositories/invoice_repository.py
# ============================================================

from app.utils.db import db_cursor


def create_invoice(patient_id, professional_id, cita_id, items, metodo_pago, estado_pago="Pendiente"):
    monto = sum(float(item.get("precioUnitario") or 0) for item in items)
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO facturas (idPaciente, idProfesional, idCita, monto, metodoPago, estadoPago)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (patient_id, professional_id, cita_id, monto, metodo_pago, estado_pago),
        )
        invoice_id = cursor.lastrowid
        for item in items:
            cursor.execute(
                "INSERT INTO itemsfactura (idFactura, descripcion, precioUnitario) VALUES (%s, %s, %s)",
                (invoice_id, item.get("descripcion"), item.get("precioUnitario")),
            )
        conn.commit()
        return invoice_id


def get_invoice_payment_info(invoice_id):
    # Datos mínimos para orquestar el cobro con Wompi (monto, dueño, estado, referencia)
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idFactura, idPaciente, monto, estadoPago, anulada, wompiReference "
            "FROM facturas WHERE idFactura = %s",
            (invoice_id,),
        )
        return cursor.fetchone()


def get_invoice_owner(invoice_id):
    # Devuelve (idPaciente, idProfesional, anulada) para validar permisos y estado
    with db_cursor() as (_, cursor):
        cursor.execute(
            "SELECT idPaciente, idProfesional, anulada FROM facturas WHERE idFactura = %s",
            (invoice_id,),
        )
        return cursor.fetchone()


def get_invoice_by_id(invoice_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT f.idFactura, f.idPaciente, f.idProfesional, f.idCita, f.monto, f.metodoPago,
                   f.estadoPago, f.anulada, f.motivoAnulacion, f.fecha,
                   rp.nombre as paciente, rpr.nombre as profesional
            FROM facturas f
            JOIN Register rp ON f.idPaciente = rp.idUsuario
            JOIN Register rpr ON f.idProfesional = rpr.idUsuario
            WHERE f.idFactura = %s
            """,
            (invoice_id,),
        )
        factura = cursor.fetchone()
        if not factura:
            return None
        cursor.execute(
            "SELECT idItem, descripcion, precioUnitario FROM itemsfactura WHERE idFactura = %s",
            (invoice_id,),
        )
        factura["items"] = cursor.fetchall()
        return factura


def list_invoices_by_patient(patient_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT f.idFactura, f.idCita, f.monto, f.metodoPago, f.estadoPago,
                   f.anulada, f.motivoAnulacion, f.fecha, r.nombre as profesional,
                   (SELECT GROUP_CONCAT(i.descripcion SEPARATOR ', ')
                    FROM itemsfactura i WHERE i.idFactura = f.idFactura) as servicios
            FROM facturas f
            JOIN Register r ON f.idProfesional = r.idUsuario
            WHERE f.idPaciente = %s
            ORDER BY f.fecha DESC
            """,
            (patient_id,),
        )
        return cursor.fetchall()


def _build_filter_clauses(filtros, base_clauses, base_params):
    clauses = list(base_clauses)
    params = list(base_params)

    if filtros.get("paciente"):
        clauses.append("f.idPaciente = %s")
        params.append(filtros["paciente"])
    if filtros.get("profesional"):
        clauses.append("f.idProfesional = %s")
        params.append(filtros["profesional"])
    if filtros.get("metodoPago"):
        clauses.append("f.metodoPago = %s")
        params.append(filtros["metodoPago"])
    estado = filtros.get("estado")
    if estado == "Anulada":
        clauses.append("f.anulada = TRUE")
    elif estado:
        clauses.append("f.estadoPago = %s AND f.anulada = FALSE")
        params.append(estado)
    if filtros.get("fecha_desde"):
        clauses.append("DATE(f.fecha) >= %s")
        params.append(filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        clauses.append("DATE(f.fecha) <= %s")
        params.append(filtros["fecha_hasta"])

    return clauses, params


def list_invoices_by_professional(professional_id, filtros=None):
    clauses, params = _build_filter_clauses(filtros or {}, ["f.idProfesional = %s"], [professional_id])
    where = " AND ".join(clauses)
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            f"""
            SELECT f.idFactura, f.idPaciente, f.idCita, f.monto, f.metodoPago, f.estadoPago,
                   f.anulada, f.motivoAnulacion, f.fecha, r.nombre as paciente
            FROM facturas f
            JOIN Register r ON f.idPaciente = r.idUsuario
            WHERE {where}
            ORDER BY f.fecha DESC
            """,
            tuple(params),
        )
        return cursor.fetchall()


def list_all_invoices(filtros=None):
    clauses, params = _build_filter_clauses(filtros or {}, ["1=1"], [])
    where = " AND ".join(clauses)
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            f"""
            SELECT f.idFactura, f.idPaciente, f.idProfesional, f.idCita, f.monto, f.metodoPago,
                   f.estadoPago, f.anulada, f.motivoAnulacion, f.fecha,
                   rp.nombre as paciente, rpr.nombre as profesional
            FROM facturas f
            JOIN Register rp ON f.idPaciente = rp.idUsuario
            JOIN Register rpr ON f.idProfesional = rpr.idUsuario
            WHERE {where}
            ORDER BY f.fecha DESC
            """,
            tuple(params),
        )
        return cursor.fetchall()


def update_payment_status(invoice_id, nuevo_estado):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE facturas SET estadoPago = %s WHERE idFactura = %s AND anulada = FALSE",
            (nuevo_estado, invoice_id),
        )
        conn.commit()
        return cursor.rowcount


def set_wompi_reference(invoice_id, reference):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE facturas SET wompiReference = %s WHERE idFactura = %s",
            (reference, invoice_id),
        )
        conn.commit()


def get_invoice_by_wompi_reference(reference):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idFactura, idPaciente, monto, estadoPago, anulada, wompiReference "
            "FROM facturas WHERE wompiReference = %s",
            (reference,),
        )
        return cursor.fetchone()


def mark_paid_by_wompi(invoice_id, transaction_id):
    # Idempotente: solo aplica si la factura sigue pendiente/parcial y no está anulada,
    # así un reintento del webhook o de la verificación por redirect no la vuelve a tocar.
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE facturas
            SET estadoPago = 'Pagado', wompiTransactionId = %s
            WHERE idFactura = %s AND anulada = FALSE AND estadoPago != 'Pagado'
            """,
            (transaction_id, invoice_id),
        )
        conn.commit()
        return cursor.rowcount


def annul_invoice(invoice_id, motivo):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE facturas SET anulada = TRUE, motivoAnulacion = %s WHERE idFactura = %s AND anulada = FALSE",
            (motivo, invoice_id),
        )
        conn.commit()
        return cursor.rowcount
