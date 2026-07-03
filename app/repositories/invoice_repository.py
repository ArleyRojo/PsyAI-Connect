from sqlalchemy import select
from app.database.session import db_session
from app.models.facturas import Facturas
from app.models.items_factura import ItemsFactura
from app.models.register import Register
from app.models.pacientes_profesional import PacientesProfesional


class InvoiceRepository:
    def create_invoice(self, patient_id, professional_id, cita_id, items, metodo_pago):
        with db_session() as session:
            monto = sum(item["precioUnitario"] for item in items)
            factura = Facturas(
                idPaciente=patient_id,
                idProfesional=professional_id,
                idCita=cita_id,
                monto=monto,
                metodoPago=metodo_pago,
                estadoPago="Pendiente",
            )
            session.add(factura)
            session.flush()
            for item in items:
                session.add(ItemsFactura(
                    idFactura=factura.idFactura,
                    descripcion=item["descripcion"],
                    precioUnitario=item["precioUnitario"],
                ))
            return factura.idFactura

    def get_invoice_by_id(self, invoice_id):
        with db_session() as session:
            factura = session.get(Facturas, invoice_id)
            if not factura:
                return None
            result = factura.to_dict()
            result["nombrePaciente"] = session.get(Register, factura.idPaciente).nombre if session.get(Register, factura.idPaciente) else None
            result["nombreProfesional"] = session.get(Register, factura.idProfesional).nombre if session.get(Register, factura.idProfesional) else None
            return result

    def list_invoices_by_patient(self, patient_id):
        with db_session() as session:
            stmt = select(Facturas).where(Facturas.idPaciente == patient_id).order_by(Facturas.fecha.desc())
            facturas = session.execute(stmt).scalars().all()
            result = []
            for f in facturas:
                d = f.to_dict()
                d["nombreProfesional"] = session.get(Register, f.idProfesional).nombre if session.get(Register, f.idProfesional) else None
                result.append(d)
            return result

    def list_invoices_by_professional(self, professional_id, estado=None, fecha_desde=None, fecha_hasta=None):
        with db_session() as session:
            stmt = select(Facturas).where(Facturas.idProfesional == professional_id)
            if estado == "Anulada":
                stmt = stmt.where(Facturas.anulada == True)
            elif estado:
                stmt = stmt.where(Facturas.anulada == False, Facturas.estadoPago == estado)
            if fecha_desde:
                stmt = stmt.where(Facturas.fecha >= fecha_desde)
            if fecha_hasta:
                stmt = stmt.where(Facturas.fecha < fecha_hasta + " 23:59:59")
            stmt = stmt.order_by(Facturas.fecha.desc())
            facturas = session.execute(stmt).scalars().all()
            result = []
            for f in facturas:
                d = f.to_dict()
                d["nombrePaciente"] = session.get(Register, f.idPaciente).nombre if session.get(Register, f.idPaciente) else None
                result.append(d)
            return result

    def list_all_invoices(self, paciente=None, profesional=None, estado=None, metodo_pago=None, fecha_desde=None, fecha_hasta=None):
        with db_session() as session:
            stmt = select(Facturas)
            if paciente:
                stmt = stmt.join(Register, Facturas.idPaciente == Register.idUsuario).where(Register.nombre.like(f"%{paciente}%"))
            if estado == "Anulada":
                stmt = stmt.where(Facturas.anulada == True)
            elif estado:
                stmt = stmt.where(Facturas.anulada == False, Facturas.estadoPago == estado)
            if metodo_pago:
                stmt = stmt.where(Facturas.metodoPago == metodo_pago)
            if fecha_desde:
                stmt = stmt.where(Facturas.fecha >= fecha_desde)
            if fecha_hasta:
                stmt = stmt.where(Facturas.fecha < fecha_hasta + " 23:59:59")
            stmt = stmt.order_by(Facturas.fecha.desc())
            facturas = session.execute(stmt).scalars().all()
            result = []
            for f in facturas:
                d = f.to_dict()
                d["nombrePaciente"] = session.get(Register, f.idPaciente).nombre if session.get(Register, f.idPaciente) else None
                d["nombreProfesional"] = session.get(Register, f.idProfesional).nombre if session.get(Register, f.idProfesional) else None
                result.append(d)
            return result

    def update_payment_status(self, invoice_id, nuevo_estado):
        with db_session() as session:
            factura = session.get(Facturas, invoice_id)
            if factura:
                factura.estadoPago = nuevo_estado

    def annul_invoice(self, invoice_id, motivo):
        with db_session() as session:
            factura = session.get(Facturas, invoice_id)
            if factura:
                factura.anulada = True
                factura.motivoAnulacion = motivo

    def set_payment_reference(self, invoice_id, referencia, id_transaccion):
        with db_session() as session:
            factura = session.get(Facturas, invoice_id)
            if factura:
                factura.referenciaPago = referencia
                factura.idTransaccionPago = id_transaccion

    def get_invoice_by_reference(self, reference):
        with db_session() as session:
            stmt = select(Facturas.idFactura).where(Facturas.referenciaPago == reference)
            row = session.execute(stmt).scalar_one_or_none()
            return row

    def get_invoice_owner(self, invoice_id):
        with db_session() as session:
            factura = session.get(Facturas, invoice_id)
            if factura:
                return (factura.idPaciente, factura.idProfesional, factura.anulada)
            return None

    def get_professional_patients(self, professional_id):
        with db_session() as session:
            stmt = select(Register.idUsuario, Register.nombre).distinct().join(
                PacientesProfesional, PacientesProfesional.idPaciente == Register.idUsuario
            ).where(PacientesProfesional.idProfesional == professional_id).order_by(Register.nombre)
            rows = session.execute(stmt).all()
            return [{"idUsuario": r[0], "nombre": r[1]} for r in rows]

    def get_invoice_stats_by_professional(self, professional_id):
        with db_session() as session:
            facturas = session.execute(
                select(Facturas).where(Facturas.idProfesional == professional_id)
            ).scalars().all()
            total_pagado = sum(float(f.monto) for f in facturas if not f.anulada and f.estadoPago == "Pagado" and f.monto)
            total_pendiente = sum(float(f.monto) for f in facturas if not f.anulada and f.estadoPago in ("Pendiente", "Parcial") and f.monto)
            total_general = sum(float(f.monto) for f in facturas if not f.anulada and f.monto)
            return {
                "totalPagado": total_pagado,
                "totalPendiente": total_pendiente,
                "totalGeneral": total_general,
            }

    def get_invoice_stats_all(self):
        with db_session() as session:
            facturas = session.execute(select(Facturas)).scalars().all()
            total_facturado = sum(float(f.monto) for f in facturas if not f.anulada and f.monto)
            total_pagado = sum(float(f.monto) for f in facturas if not f.anulada and f.estadoPago == "Pagado" and f.monto)
            total_pendiente = sum(float(f.monto) for f in facturas if not f.anulada and f.estadoPago in ("Pendiente", "Parcial") and f.monto)
            anuladas = sum(1 for f in facturas if f.anulada)
            return {
                "totalFacturado": total_facturado,
                "totalPagado": total_pagado,
                "totalPendiente": total_pendiente,
                "anuladas": anuladas,
            }
