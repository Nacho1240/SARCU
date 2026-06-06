"""
test_scomp.py — Tests unitarios para scomp (servicio de comprobantes)

Ejecutar:
    pytest test_scomp.py -v

Dependencias:
    pip install pytest pytest-mock supabase

Variables de entorno necesarias (o se usan mocks automáticamente):
    SUPABASE_URL, SUPABASE_SERVICE_KEY
"""

import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────
# FIXTURES DE SUPABASE MOCKEADO
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-service-key")

    with patch("supabase.create_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def sb(mock_supabase):
    return mock_supabase


@pytest.fixture(autouse=True)
def reload_module(mock_supabase):
    import importlib
    import sys

    if "scomp" in sys.modules:
        del sys.modules["scomp"]

    with patch("supabase.create_client", return_value=mock_supabase):
        import scomp
        yield scomp


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _build_chain(sb, responses_by_table: dict):
    """
    Configura sb.table() para devolver respuestas distintas según
    el nombre de tabla. responses_by_table = {"profiles": data, "gastos": data}
    """
    def table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value  = chain
        chain.update.return_value  = chain
        chain.eq.return_value      = chain
        chain.single.return_value  = chain
        chain.execute.return_value = MagicMock(data=responses_by_table.get(name))
        return chain

    sb.table.side_effect = table_side_effect


# ─────────────────────────────────────────────
# DATOS COMUNES
# ─────────────────────────────────────────────

OPERARIO_ID = "aaa-111-operario"
CONTADOR_ID = "bbb-222-contador"
GASTO_ID    = "ccc-333-gasto"

URL_PUBLICA = (
    "https://fake.supabase.co/storage/v1/object/public/comprobantes/2025/06/boleta.jpg"
)

PERFIL_OPERARIO = {"id": OPERARIO_ID, "rol": "operario"}
PERFIL_CONTADOR = {"id": CONTADOR_ID, "rol": "contador"}

GASTO_PENDIENTE = {
    "id":              GASTO_ID,
    "operario_id":     OPERARIO_ID,
    "estado":          "pendiente",
    "comprobante_url": None,
}
GASTO_CON_URL = {**GASTO_PENDIENTE, "comprobante_url": URL_PUBLICA}
GASTO_APROBADO = {**GASTO_PENDIENTE, "estado": "aprobado"}


# ─────────────────────────────────────────────────────────
# TEST: subir_comprobante
# ─────────────────────────────────────────────────────────

class TestSubirComprobante:

    def test_operario_vincula_url_correctamente(self, reload_module, sb):
        """Operario con gasto pendiente propio puede vincular una URL."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_PENDIENTE,
        })

        resultado = reload_module.subir_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url":      URL_PUBLICA,
        })

        assert resultado["status"] == "ok"
        assert resultado["url"]      == URL_PUBLICA
        assert resultado["gasto_id"] == GASTO_ID

    def test_contador_no_puede_subir(self, reload_module, sb):
        """Solo operarios pueden subir comprobantes."""
        _build_chain(sb, {"profiles": PERFIL_CONTADOR})

        resultado = reload_module.subir_comprobante({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
            "url":      URL_PUBLICA,
        })

        assert resultado["status"] == "error"
        assert "operario" in resultado["mensaje"].lower()

    def test_falla_sin_url(self, reload_module, sb):
        """URL vacía debe ser rechazada."""
        _build_chain(sb, {"profiles": PERFIL_OPERARIO})

        resultado = reload_module.subir_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url":      "",
        })

        assert resultado["status"] == "error"
        assert "faltan" in resultado["mensaje"].lower()

    def test_falla_sin_gasto_id(self, reload_module, sb):
        """gasto_id obligatorio."""
        _build_chain(sb, {"profiles": PERFIL_OPERARIO})

        resultado = reload_module.subir_comprobante({
            "user_id": OPERARIO_ID,
            "url":     URL_PUBLICA,
        })

        assert resultado["status"] == "error"

    def test_falla_en_gasto_ajeno(self, reload_module, sb):
        """Operario no puede vincular comprobante a gasto de otro operario."""
        gasto_ajeno = {**GASTO_PENDIENTE, "operario_id": "otro-operario"}
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   gasto_ajeno,
        })

        resultado = reload_module.subir_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url":      URL_PUBLICA,
        })

        assert resultado["status"] == "error"
        assert "permiso" in resultado["mensaje"].lower()

    def test_falla_en_gasto_aprobado(self, reload_module, sb):
        """No se puede adjuntar comprobante a gasto ya revisado."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_APROBADO,
        })

        resultado = reload_module.subir_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url":      URL_PUBLICA,
        })

        assert resultado["status"] == "error"
        assert "pendiente" in resultado["mensaje"].lower()


# ─────────────────────────────────────────────────────────
# TEST: obtener_url
# ─────────────────────────────────────────────────────────

class TestObtenerUrl:

    def test_devuelve_url_si_existe(self, reload_module, sb):
        """Cualquier usuario autenticado puede obtener la URL del comprobante."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_CON_URL,
        })

        resultado = reload_module.obtener_url({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "ok"
        assert resultado["url"] == URL_PUBLICA

    def test_falla_si_no_hay_comprobante(self, reload_module, sb):
        """Gasto sin comprobante_url debe retornar error descriptivo."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_PENDIENTE,   # comprobante_url = None
        })

        resultado = reload_module.obtener_url({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "comprobante" in resultado["mensaje"].lower()

    def test_falla_si_gasto_no_existe(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   None,
        })

        resultado = reload_module.obtener_url({
            "user_id":  OPERARIO_ID,
            "gasto_id": "no-existe",
        })

        assert resultado["status"] == "error"
        assert "no encontrado" in resultado["mensaje"].lower()

    def test_falla_si_usuario_no_existe(self, reload_module, sb):
        _build_chain(sb, {"profiles": None})

        resultado = reload_module.obtener_url({
            "user_id":  "usuario-fantasma",
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"

    def test_contador_puede_obtener_url(self, reload_module, sb):
        """Contador también puede ver la URL de cualquier comprobante."""
        _build_chain(sb, {
            "profiles": PERFIL_CONTADOR,
            "gastos":   GASTO_CON_URL,
        })

        resultado = reload_module.obtener_url({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "ok"
        assert resultado["url"] == URL_PUBLICA


# ─────────────────────────────────────────────────────────
# TEST: vincular_comprobante
# ─────────────────────────────────────────────────────────

class TestVincularComprobante:

    def test_vincular_es_equivalente_a_subir(self, reload_module, sb):
        """
        vincular_comprobante reutiliza subir_comprobante,
        por lo tanto debe comportarse igual ante un caso válido.
        """
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_PENDIENTE,
        })

        resultado = reload_module.vincular_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url":      URL_PUBLICA,
        })

        assert resultado["status"] == "ok"
        assert resultado["url"] == URL_PUBLICA

    def test_vincular_falla_en_gasto_ajeno(self, reload_module, sb):
        gasto_ajeno = {**GASTO_PENDIENTE, "operario_id": "otro"}
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   gasto_ajeno,
        })

        resultado = reload_module.vincular_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url":      URL_PUBLICA,
        })

        assert resultado["status"] == "error"


# ─────────────────────────────────────────────────────────
# TEST: eliminar_comprobante
# ─────────────────────────────────────────────────────────

class TestEliminarComprobante:

    def test_operario_elimina_comprobante_propio(self, reload_module, sb):
        """Operario puede eliminar su propio comprobante en gasto pendiente."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_CON_URL,
        })

        # Mock del storage
        sb.storage.from_.return_value.remove.return_value = MagicMock()

        resultado = reload_module.eliminar_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "ok"
        assert "eliminado" in resultado["mensaje"].lower()

    def test_llama_a_storage_remove_con_ruta_correcta(self, reload_module, sb):
        """Verifica que se extrae la ruta relativa correcta del bucket."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_CON_URL,
        })

        storage_mock = MagicMock()
        sb.storage.from_.return_value = storage_mock

        reload_module.eliminar_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        # Debe llamarse con la ruta sin el prefijo del bucket
        storage_mock.remove.assert_called_once()
        ruta_llamada = storage_mock.remove.call_args[0][0][0]
        assert ruta_llamada == "2025/06/boleta.jpg"
        assert "comprobantes" not in ruta_llamada   # el bucket no va en la ruta

    def test_falla_si_no_hay_comprobante(self, reload_module, sb):
        """Gasto sin comprobante no puede eliminarse."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_PENDIENTE,  # comprobante_url = None
        })

        resultado = reload_module.eliminar_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "comprobante" in resultado["mensaje"].lower()

    def test_falla_en_gasto_aprobado(self, reload_module, sb):
        """No se puede eliminar comprobante de un gasto ya revisado."""
        gasto_aprobado_con_url = {**GASTO_CON_URL, "estado": "aprobado"}
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   gasto_aprobado_con_url,
        })

        resultado = reload_module.eliminar_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "revisado" in resultado["mensaje"].lower()

    def test_falla_en_gasto_ajeno(self, reload_module, sb):
        gasto_ajeno = {**GASTO_CON_URL, "operario_id": "otro-operario"}
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   gasto_ajeno,
        })

        resultado = reload_module.eliminar_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "permiso" in resultado["mensaje"].lower()

    def test_contador_no_puede_eliminar(self, reload_module, sb):
        """Contador no tiene permiso para eliminar comprobantes."""
        _build_chain(sb, {"profiles": PERFIL_CONTADOR})

        resultado = reload_module.eliminar_comprobante({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "operario" in resultado["mensaje"].lower()

    def test_storage_error_devuelve_error_descriptivo(self, reload_module, sb):
        """Si el storage falla, el error debe llegar limpio al cliente."""
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos":   GASTO_CON_URL,
        })

        sb.storage.from_.return_value.remove.side_effect = Exception("Connection timeout")

        resultado = reload_module.eliminar_comprobante({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "storage" in resultado["mensaje"].lower()