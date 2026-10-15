import os
import json
import tempfile
from datetime import datetime
from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from apps.authentication.models import Register
from apps.billing.models import Facturas, ItemsFactura


@override_settings(DEBUG=True)
class LimpiarFacturasCommandTest(TestCase):
    def setUp(self):
        self.paciente = Register.objects.create_user(email="pac@test.com", password="pass1234", nombre="Paciente Test", rol="paciente")
        self.profesional = Register.objects.create_user(email="pro@test.com", password="pass1234", nombre="Profesional Test", rol="profesional")
        self.other_paciente = Register.objects.create_user(email="pac2@test.com", password="pass1234", nombre="Otro Paciente", rol="paciente")

        # crear facturas de prueba
        self.f1 = Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pendiente")
        ItemsFactura.objects.create(idFactura=self.f1, descripcion="Consulta", precioUnitario=Decimal("100000"))
        self.f2 = Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("200000"), estadoPago="Pagado")
        ItemsFactura.objects.create(idFactura=self.f2, descripcion="Terapia", precioUnitario=Decimal("200000"))
        self.f3 = Facturas.objects.create(idPaciente=self.other_paciente, idProfesional=self.profesional, monto=Decimal("150000"), estadoPago="Pendiente")
        ItemsFactura.objects.create(idFactura=self.f3, descripcion="Otro", precioUnitario=Decimal("150000"))

        # agregar evidencia a f2
        img = SimpleUploadedFile("test.png", b"fakeimage", content_type="image/png")
        self.f2.evidencia.save("evidencia_test.png", img, save=True)

        # ensure backups dir exists
        self.backup_dir = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def tearDown(self):
        # clean backup files
        if os.path.exists(self.backup_dir):
            for f in os.listdir(self.backup_dir):
                try:
                    os.remove(os.path.join(self.backup_dir, f))
                except:
                    pass

    def test_dry_run_does_not_delete(self):
        out = call_command("limpiar_facturas", stdout=None)
        # dry-run should not delete
        self.assertEqual(Facturas.objects.count(), 3)
        self.assertEqual(ItemsFactura.objects.count(), 3)
        self.assertTrue(self.f2.evidencia.storage.exists(self.f2.evidencia.name))

    def test_yes_deletes_all(self):
        call_command("limpiar_facturas", "--yes", stdout=None)
        self.assertEqual(Facturas.objects.count(), 0)
        self.assertEqual(ItemsFactura.objects.count(), 0)
        # evidence file should be gone
        self.assertFalse(self.f2.evidencia.storage.exists(self.f2.evidencia.name))

    def test_force_prod_required_when_debug_false(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(Exception):
                call_command("limpiar_facturas", "--yes", stdout=None)
            # with --force-prod should work
            call_command("limpiar_facturas", "--yes", "--force-prod", stdout=None)
            self.assertEqual(Facturas.objects.count(), 0)

    def test_filter_by_paciente(self):
        call_command("limpiar_facturas", "--yes", "--paciente", str(self.paciente.idUsuario), stdout=None)
        # only paciente's facturas deleted (f1 and f2)
        self.assertEqual(Facturas.objects.count(), 1)
        remaining = Facturas.objects.first()
        self.assertEqual(remaining.idFactura, self.f3.idFactura)
        # items of deleted facturas also gone
        self.assertEqual(ItemsFactura.objects.count(), 1)

    def test_filter_by_profesional_name(self):
        # filter by professional name
        call_command("limpiar_facturas", "--yes", "--profesional", "Profesional Test", stdout=None)
        self.assertEqual(Facturas.objects.count(), 0)

    def test_backup_created(self):
        call_command("limpiar_facturas", "--yes", stdout=None)
        # find backup file
        files = os.listdir(self.backup_dir)
        backup_files = [f for f in files if f.startswith("billing_") and f.endswith(".json")]
        self.assertTrue(backup_files)
        backup_path = os.path.join(self.backup_dir, backup_files[0])
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # should contain 3 facturas
        self.assertEqual(len(data), 3)
        # structure check
        for obj in data:
            self.assertIn("model", obj)
            self.assertEqual(obj["model"], "billing.facturas")

    def test_no_backup_option(self):
        call_command("limpiar_facturas", "--yes", "--no-backup", stdout=None)
        files = os.listdir(self.backup_dir)
        backup_files = [f for f in files if f.startswith("billing_") and f.endswith(".json")]
        self.assertEqual(len(backup_files), 0)