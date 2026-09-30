import pytest
from decimal import Decimal

from apps.billing.repositories import InvoiceRepository
from apps.billing.models import Facturas, ItemsFactura
from apps.authentication.models import Register


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def repo():
    return InvoiceRepository()


@pytest.fixture
def patient(db):
    return Register.objects.create_user(
        email="patient@test.com", nombre="Paciente Test", password="pass", rol="paciente",
    )


@pytest.fixture
def professional(db):
    return Register.objects.create_user(
        email="pro@test.com", nombre="Profesional Test", password="pass", rol="profesional",
    )


@pytest.fixture
def sample_invoice(patient, professional):
    return Facturas.objects.create(
        idPaciente=patient,
        idProfesional=professional,
        idCita=1,
        monto=Decimal("50000.00"),
        metodoPago="tarjeta",
        estadoPago="Pendiente",
    )


# ── create_invoice ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateInvoice:
    def test_creates_invoice_and_items(self, repo, patient, professional):
        items = [
            {"descripcion": "Sesion 1", "precioUnitario": Decimal("30000.00")},
            {"descripcion": "Sesion 2", "precioUnitario": Decimal("20000.00")},
        ]
        invoice_id = repo.create_invoice(patient.idUsuario, professional.idUsuario, 5, items, "tarjeta")

        factura = Facturas.objects.get(idFactura=invoice_id)
        assert factura.idPaciente_id == patient.idUsuario
        assert factura.idProfesional_id == professional.idUsuario
        assert factura.idCita == 5
        assert factura.monto == Decimal("50000.00")
        assert factura.metodoPago == "tarjeta"
        assert factura.estadoPago == "Pendiente"

        db_items = list(ItemsFactura.objects.filter(idFactura=factura))
        assert len(db_items) == 2
        assert db_items[0].descripcion == "Sesion 1"
        assert db_items[1].descripcion == "Sesion 2"

    def test_creates_invoice_with_single_item(self, repo, patient, professional):
        items = [{"descripcion": "Unica sesion", "precioUnitario": Decimal("100000.00")}]
        invoice_id = repo.create_invoice(patient.idUsuario, professional.idUsuario, None, items, "banco")

        factura = Facturas.objects.get(idFactura=invoice_id)
        assert factura.monto == Decimal("100000.00")
        assert factura.idCita is None
        assert factura.metodoPago == "banco"

        db_items = list(ItemsFactura.objects.filter(idFactura=factura))
        assert len(db_items) == 1


# ── get_invoice_by_id ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGetInvoiceById:
    def test_returns_dict_when_found(self, repo, sample_invoice):
        result = repo.get_invoice_by_id(sample_invoice.idFactura)
        assert result is not None
        assert result["idFactura"] == sample_invoice.idFactura
        assert result["idPaciente"] == sample_invoice.idPaciente_id
        assert result["idProfesional"] == sample_invoice.idProfesional_id
        assert result["nombrePaciente"] == "Paciente Test"
        assert result["nombreProfesional"] == "Profesional Test"

    def test_returns_none_when_not_found(self, repo):
        result = repo.get_invoice_by_id(999999)
        assert result is None

    def test_includes_items(self, repo, sample_invoice):
        ItemsFactura.objects.create(
            idFactura=sample_invoice, descripcion="Item A", precioUnitario=Decimal("10000.00"),
        )
        result = repo.get_invoice_by_id(sample_invoice.idFactura)
        assert len(result["items"]) == 1
        assert result["items"][0]["descripcion"] == "Item A"


# ── list_invoices_by_patient ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestListInvoicesByPatient:
    def test_returns_list_for_patient(self, repo, sample_invoice, patient):
        result = repo.list_invoices_by_patient(patient.idUsuario)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert any(r["idFactura"] == sample_invoice.idFactura for r in result)

    def test_returns_empty_for_unknown_patient(self, repo):
        result = repo.list_invoices_by_patient(999999)
        assert result == []

    def test_includes_professional_name(self, repo, sample_invoice, patient):
        result = repo.list_invoices_by_patient(patient.idUsuario)
        entry = next(r for r in result if r["idFactura"] == sample_invoice.idFactura)
        assert entry["nombreProfesional"] == "Profesional Test"


# ── list_invoices_by_professional ────────────────────────────────────────────


@pytest.mark.django_db
class TestListInvoicesByProfessional:
    def test_returns_list_for_professional(self, repo, sample_invoice, professional):
        result = repo.list_invoices_by_professional(professional.idUsuario)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert any(r["idFactura"] == sample_invoice.idFactura for r in result)

    def test_returns_empty_for_unknown_professional(self, repo):
        result = repo.list_invoices_by_professional(999999)
        assert result == []

    def test_filters_by_estado(self, repo, patient, professional):
        Facturas.objects.create(
            idPaciente=patient, idProfesional=professional,
            monto=Decimal("10000.00"), metodoPago="tarjeta", estadoPago="Pagado",
        )
        pendiente = Facturas.objects.create(
            idPaciente=patient, idProfesional=professional,
            monto=Decimal("20000.00"), metodoPago="tarjeta", estadoPago="Pendiente",
        )
        result = repo.list_invoices_by_professional(professional.idUsuario, estado="Pendiente")
        ids = [r["idFactura"] for r in result]
        assert pendiente.idFactura in ids

    def test_filters_by_estado_anulada(self, repo, patient, professional):
        anulada = Facturas.objects.create(
            idPaciente=patient, idProfesional=professional,
            monto=Decimal("5000.00"), metodoPago="banco", estadoPago="Pendiente", anulada=True,
        )
        Facturas.objects.create(
            idPaciente=patient, idProfesional=professional,
            monto=Decimal("7000.00"), metodoPago="banco", estadoPago="Pagado", anulada=False,
        )
        result = repo.list_invoices_by_professional(professional.idUsuario, estado="Anulada")
        ids = [r["idFactura"] for r in result]
        assert anulada.idFactura in ids

    def test_includes_patient_name(self, repo, sample_invoice, professional):
        result = repo.list_invoices_by_professional(professional.idUsuario)
        entry = next(r for r in result if r["idFactura"] == sample_invoice.idFactura)
        assert entry["nombrePaciente"] == "Paciente Test"


# ── list_all_invoices ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestListAllInvoices:
    def test_returns_all_without_filters(self, repo, sample_invoice):
        result = repo.list_all_invoices()
        assert any(r["idFactura"] == sample_invoice.idFactura for r in result)

    def test_filters_by_profesional(self, repo, sample_invoice, professional):
        otro = Register.objects.create_user(
            email="otro@test.com", nombre="Otro Profesional",
            password="pass", rol="profesional",
        )
        ajena = Facturas.objects.create(
            idPaciente=professional, idProfesional=otro,
            monto=Decimal("9000.00"), metodoPago="tarjeta", estadoPago="Pagado",
        )
        result = repo.list_all_invoices(profesional="Profesional Test")
        ids = [r["idFactura"] for r in result]
        assert sample_invoice.idFactura in ids
        assert ajena.idFactura not in ids

    def test_filter_profesional_no_encuentra_devuelve_vacio(
        self, repo, sample_invoice
    ):
        result = repo.list_all_invoices(profesional="Nombre Inexistente")
        assert result == []

    def test_filters_by_profesional_and_paciente(self, repo, sample_invoice):
        result = repo.list_all_invoices(
            profesional="Profesional Test", paciente="Otro",
        )
        assert result == []

    def test_filters_by_metodo_pago(self, repo, patient, professional):
        tarjeta = Facturas.objects.create(
            idPaciente=patient, idProfesional=professional,
            monto=Decimal("1000.00"), metodoPago="tarjeta", estadoPago="Pagado",
        )
        banco = Facturas.objects.create(
            idPaciente=patient, idProfesional=professional,
            monto=Decimal("2000.00"), metodoPago="banco", estadoPago="Pagado",
        )
        result = repo.list_all_invoices(metodo_pago="banco")
        ids = [r["idFactura"] for r in result]
        assert banco.idFactura in ids
        assert tarjeta.idFactura not in ids

    def test_filters_by_estado_anulada(self, repo, patient, professional):
        anulada = Facturas.objects.create(
            idPaciente=patient, idProfesional=professional,
            monto=Decimal("1000.00"), metodoPago="tarjeta",
            estadoPago="Pendiente", anulada=True,
        )
        result = repo.list_all_invoices(estado="Anulada")
        ids = [r["idFactura"] for r in result]
        assert anulada.idFactura in ids

    def test_includes_both_names(self, repo, sample_invoice):
        result = repo.list_all_invoices(profesional="Profesional Test")
        entry = next(
            r for r in result if r["idFactura"] == sample_invoice.idFactura
        )
        assert entry["nombrePaciente"] == "Paciente Test"
        assert entry["nombreProfesional"] == "Profesional Test"


# ── update_payment_status ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUpdatePaymentStatus:
    def test_updates_status(self, repo, sample_invoice):
        result = repo.update_payment_status(sample_invoice.idFactura, "Pagado")
        assert result is True
        sample_invoice.refresh_from_db()
        assert sample_invoice.estadoPago == "Pagado"

    def test_returns_false_for_nonexistent(self, repo):
        result = repo.update_payment_status(999999, "Pagado")
        assert result is False

    def test_updates_to_cancelado(self, repo, sample_invoice):
        repo.update_payment_status(sample_invoice.idFactura, "Cancelado")
        sample_invoice.refresh_from_db()
        assert sample_invoice.estadoPago == "Cancelado"


# ── annul_invoice ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAnnulInvoice:
    def test_marks_as_annulled(self, repo, sample_invoice):
        result = repo.annul_invoice(sample_invoice.idFactura, "Motivo de prueba")
        assert result is True
        sample_invoice.refresh_from_db()
        assert sample_invoice.anulada is True
        assert sample_invoice.motivoAnulacion == "Motivo de prueba"

    def test_returns_false_for_nonexistent(self, repo):
        result = repo.annul_invoice(999999, "Motivo")
        assert result is False

    def test_preserves_other_fields(self, repo, sample_invoice):
        repo.annul_invoice(sample_invoice.idFactura, "Anular")
        sample_invoice.refresh_from_db()
        assert sample_invoice.monto == Decimal("50000.00")
        assert sample_invoice.estadoPago == "Pendiente"


# ── get_invoice_owner ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGetInvoiceOwner:
    def test_returns_tuple_when_found(self, repo, sample_invoice, patient, professional):
        result = repo.get_invoice_owner(sample_invoice.idFactura)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert result[0] == patient.idUsuario
        assert result[1] == professional.idUsuario
        assert result[2] is False  # anulada

    def test_returns_none_when_not_found(self, repo):
        result = repo.get_invoice_owner(999999)
        assert result is None

    def test_returns_annulled_flag(self, repo, sample_invoice):
        repo.annul_invoice(sample_invoice.idFactura, "Anular")
        result = repo.get_invoice_owner(sample_invoice.idFactura)
        assert result[2] is True
