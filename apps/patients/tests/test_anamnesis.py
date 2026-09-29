import datetime
import pytest
from apps.authentication.models import Register
from apps.patients.models import Anamnesis, Familiar
from apps.patients.repositories import PatientRepository
from apps.patients.services import PatientService
from apps.patients.views import AnamnesisViewSet
from apps.core.permissions import IsAuthenticatedDRF


@pytest.fixture
def repo():
    return PatientRepository()


@pytest.fixture
def service():
    return PatientService()


@pytest.fixture
def profesional_user(db):
    return Register.objects.create_user(
        email="doctor@psyai.com",
        nombre="Dr. Mario",
        password="Password123",
        rol="profesional",
    )


@pytest.fixture
def profesional_otro(db):
    return Register.objects.create_user(
        email="doctor2@psyai.com",
        nombre="Dra. Lucia",
        password="Password123",
        rol="profesional",
    )


@pytest.fixture
def paciente_user(db):
    return Register.objects.create_user(
        email="paciente@psyai.com",
        nombre="Carlos Gomez",
        password="Password123",
        rol="paciente",
    )


@pytest.fixture
def valid_anamnesis_payload():
    return {
        "tipoDocumento": "CC",
        "numeroDocumento": "1020304050",
        "fechaNacimiento": "1995-05-15",
        "genero": "Masculino",
        "estadoCivil": "Soltero/a",
        "telefonoPrincipal": "3001234567",
        "direccionResidencia": "Calle 10 # 20-30",
        "ciudad": "Bogota",
        "nivelEscolar": "universitario",
        "ocupacion": "Ingeniero",
        "rangoIngresosMensuales": "2SMM4SMM",
        "motivoConsulta": "Presenta sintomas de ansiedad en entornos laborales.",
        "familiares": [
            {
                "tipoParentesco": "MADRE",
                "nombreCompleto": "Rosa Gomez",
                "edad": 55,
                "vivo": True,
                "estadoSalud": "sano",
                "diagnosticoOEnfermedad": None,
                "ocupacion": "Docente",
                "telefono": "3109876543",
                "orden": 0,
            },
            {
                "tipoParentesco": "PADRE",
                "nombreCompleto": "Alberto Gomez",
                "edad": 60,
                "vivo": True,
                "estadoSalud": "enfermedad_cronica",
                "diagnosticoOEnfermedad": "Hipertension arterial",
                "ocupacion": "Comerciante",
                "telefono": "3112233445",
                "orden": 1,
            },
        ],
    }


# ── Repositorio & Modelos ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnamnesisRepository:
    def test_create_anamnesis_con_familiares_y_cascade(
        self, repo, profesional_user, paciente_user, valid_anamnesis_payload
    ):
        data = valid_anamnesis_payload.copy()
        familiares_data = data.pop("familiares")

        anamnesis = repo.create_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, data, familiares_data
        )

        assert anamnesis.idAnamnesis is not None
        assert anamnesis.idPaciente_id == paciente_user.idUsuario
        assert anamnesis.idProfesional_id == profesional_user.idUsuario
        assert anamnesis.numeroDocumento == "1020304050"

        # Verificar familiares
        familiares = Familiar.objects.filter(idAnamnesis=anamnesis)
        assert familiares.count() == 2
        assert familiares.filter(tipoParentesco="MADRE").exists()
        assert familiares.filter(tipoParentesco="PADRE").exists()

        # Verificar CASCADE al eliminar la anamnesis
        anamnesis_id = anamnesis.idAnamnesis
        anamnesis.delete()
        assert Familiar.objects.filter(idAnamnesis_id=anamnesis_id).count() == 0

    def test_update_anamnesis_y_replace_familiares(
        self, repo, profesional_user, paciente_user, valid_anamnesis_payload
    ):
        data = valid_anamnesis_payload.copy()
        familiares_data = data.pop("familiares")

        anamnesis = repo.create_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, data, familiares_data
        )

        # Actualizar datos de anamnesis
        update_data = {
            "ocupacion": "Arquitecto",
            "motivoConsulta": "Ansiedad y dificultad para conciliar el sueno.",
        }
        anamnesis = repo.update_anamnesis(anamnesis, update_data)
        assert anamnesis.ocupacion == "Arquitecto"
        assert "dificultad para conciliar" in anamnesis.motivoConsulta

        # Reemplazar familiares
        nuevos_familiares = [
            {
                "tipoParentesco": "HERMANO",
                "nombreCompleto": "Santiago Gomez",
                "edad": 22,
                "vivo": True,
                "estadoSalud": "sano",
                "orden": 0,
            }
        ]
        repo.replace_familiares(anamnesis, nuevos_familiares)
        fams = Familiar.objects.filter(idAnamnesis=anamnesis)
        assert fams.count() == 1
        assert fams.first().tipoParentesco == "HERMANO"


# ── Servicio de Anamnesis ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnamnesisService:
    def test_registrar_anamnesis_exitoso(
        self, service, profesional_user, paciente_user, valid_anamnesis_payload
    ):
        res, status_code = service.registrar_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, valid_anamnesis_payload
        )
        assert status_code == 201
        assert res["success"] is True
        assert res["anamnesis"]["idPaciente"] == paciente_user.idUsuario
        assert len(res["anamnesis"]["familiares"]) == 2

    def test_registrar_anamnesis_duplicada_retorna_409(
        self, service, profesional_user, paciente_user, valid_anamnesis_payload
    ):
        # Primera creación
        service.registrar_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, valid_anamnesis_payload.copy()
        )

        # Intento de duplicado
        res, status_code = service.registrar_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, valid_anamnesis_payload.copy()
        )
        assert status_code == 409
        assert res["success"] is False
        assert "Ya existe una anamnesis" in res["message"]

    def test_registrar_anamnesis_campos_obligatorios_retorna_400(
        self, service, profesional_user, paciente_user
    ):
        payload_incompleto = {
            "tipoDocumento": "CC",
            # faltan: fechaNacimiento, telefonoPrincipal, direccionResidencia, nivelEscolar, motivoConsulta
        }
        res, status_code = service.registrar_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, payload_incompleto
        )
        assert status_code == 400
        assert res["success"] is False
        assert "Campos obligatorios faltantes" in res["message"]

    def test_obtener_anamnesis_ajena_retorna_403(
        self, service, profesional_user, profesional_otro, paciente_user, valid_anamnesis_payload
    ):
        service.registrar_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, valid_anamnesis_payload
        )

        # Otro profesional intenta consultar la anamnesis
        res, status_code = service.get_anamnesis(
            paciente_user.idUsuario, profesional_otro.idUsuario
        )
        assert status_code == 403
        assert res["success"] is False
        assert "No autorizado" in res["message"]

    def test_actualizar_anamnesis_ajena_retorna_403(
        self, service, profesional_user, profesional_otro, paciente_user, valid_anamnesis_payload
    ):
        service.registrar_anamnesis(
            paciente_user.idUsuario, profesional_user.idUsuario, valid_anamnesis_payload
        )

        res, status_code = service.actualizar_anamnesis(
            paciente_user.idUsuario, profesional_otro.idUsuario, {"ocupacion": "Piloto"}
        )
        assert status_code == 403
        assert res["success"] is False

    def test_edad_calculada_property(self, profesional_user, paciente_user):
        hoy = datetime.date.today()
        nacimiento = hoy.replace(year=hoy.year - 30)
        anamnesis = Anamnesis.objects.create(
            idPaciente=paciente_user,
            idProfesional=profesional_user,
            fechaNacimiento=nacimiento,
            telefonoPrincipal="3000000000",
            direccionResidencia="Cra 1",
            nivelEscolar="universitario",
            motivoConsulta="Prueba",
        )
        assert anamnesis.edad_calculada == 30


# ── ViewSet & Endpoints ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnamnesisViewSet:
    def test_viewset_retrieve_create_update(
        self, rf, profesional_user, paciente_user, valid_anamnesis_payload
    ):
        def _mock_auth(self, request, view):
            request.user_id = profesional_user.idUsuario
            request.user_role = "profesional"
            request.user_name = profesional_user.nombre
            return True

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(IsAuthenticatedDRF, "has_permission", _mock_auth)

            view = AnamnesisViewSet.as_view(
                {"get": "retrieve", "post": "create", "put": "update", "delete": "destroy"}
            )

            # 1. GET inicial -> 404
            req_get = rf.get(f"/api/paciente/{paciente_user.idUsuario}/anamnesis")
            resp_get = view(req_get, paciente_id=paciente_user.idUsuario)
            assert resp_get.status_code == 404

            # 2. POST create -> 201
            req_post = rf.post(
                f"/api/paciente/{paciente_user.idUsuario}/anamnesis",
                valid_anamnesis_payload,
                format="json",
            )
            resp_post = view(req_post, paciente_id=paciente_user.idUsuario)
            assert resp_post.status_code == 201
            assert resp_post.data["success"] is True

            # 3. GET retrieve tras crear -> 200
            req_get2 = rf.get(f"/api/paciente/{paciente_user.idUsuario}/anamnesis")
            resp_get2 = view(req_get2, paciente_id=paciente_user.idUsuario)
            assert resp_get2.status_code == 200
            assert resp_get2.data["anamnesis"]["numeroDocumento"] == "1020304050"

            # 4. PUT update -> 200
            req_put = rf.put(
                f"/api/paciente/{paciente_user.idUsuario}/anamnesis",
                {"ocupacion": "Desarrollador Senior"},
                format="json",
            )
            resp_put = view(req_put, paciente_id=paciente_user.idUsuario)
            assert resp_put.status_code == 200
            assert resp_put.data["anamnesis"]["ocupacion"] == "Desarrollador Senior"
