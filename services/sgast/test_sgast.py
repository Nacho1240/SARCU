"""
test_sgast.py — Tests unitarios para sgast (servicio de gastos)

Ejecutar:
    pytest test_sgast.py -v

Dependencias:
    pip install pytest pytest-mock

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
    """
    Parchea create_client antes de que sgast lo importe.
    Devuelve el mock del cliente para que cada test configure respuestas.
    """
    mock_client = MagicMock()
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-service-key")

    with patch("supabase.create_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def sb(mock_supabase):
    """Alias corto para el cliente mockeado."""
    return mock_supabase


def _mock_table(sb, data=None, single=False, error=False):
    """
    Helper para encadenar sb.table(...).select/insert/update/delete/single/execute.
    Configura la cadena completa de llamadas fluidas de supabase-py.
    """
    result = MagicMock()
    result.data = data if not error else None

    chain = MagicMock()
    chain.select.return_value  = chain
    chain.insert.return_value  = chain
    chain.update.return_value  = chain
    chain.delete.return_value  = chain
    chain.eq.return_value      = chain
    chain.gte.return_value     = chain
    chain.lte.return_value     = chain
    chain.order.return_value   = chain
    chain.single.return_value  = chain
    chain.execute.return_value = result

    sb.table.return_value = chain
    return chain


# ─────────────────────────────────────────────
# IMPORTAR FUNCIONES BAJO TEST
# (se hace aquí para que los mocks ya estén activos)
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reload_module(mock_supabase):
    """
    Re-importa el módulo sgast en cada test para que tome el mock fresco.
    Ajusta el import path si sgast está en un subdirectorio.
    """
    import importlib
    import sys

    # Eliminar caché si existe
    if "sgast" in sys.modules:
        del sys.modules["sgast"]

    with patch("supabase.create_client", return_value=mock_supabase):
        import sgast
        yield sgast


# ─────────────────────────────────────────────
# DATOS COMUNES DE PRUEBA
# ─────────────────────────────────────────────

OPERARIO_ID = "aaa-111-operario"
CONTADOR_ID = "bbb-222-contador"
GASTO_ID    = "ccc-333-gasto"

PERFIL_OPERARIO = {
    "id":    OPERARIO_ID,
    "nombre":"Juan Operario",
    "email": "juan@scg.cl",
    "rol":   "operario",
    "activo": True,
}
PERFIL_CONTADOR = {
    "id":    CONTADOR_ID,
    "nombre":"María Contadora",
    "email": "maria@scg.cl",
    "rol":   "contador",
    "activo": True,
}
GASTO_PENDIENTE = {
    "id":              GASTO_ID,
    "operario_id":     OPERARIO_ID,
    "monto":           15000.00,
    "descripcion":     "Compra de materiales",
    "fecha":           "2025-06-01",
    "estado":          "pendiente",
    "comprobante_url": None,
    "contador_id":     None,
    "fecha_revision":  None,
    "motivo_rechazo":  None,
}


# ─────────────────────────────────────────────────────────
# TEST: crear_gasto
# ─────────────────────────────────────────────────────────

class TestCrearGasto:

    def test_crea_gasto_ok(self, reload_module, sb):
        """Operario con campos válidos crea un gasto exitosamente."""
        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.insert.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain

            if name == "profiles":
                chain.execute.return_value = MagicMock(data=PERFIL_OPERARIO)
            else:  # gastos
                chain.execute.return_value = MagicMock(data=[GASTO_PENDIENTE])

            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.crear_gasto({
            "user_id":     OPERARIO_ID,
            "monto":       15000,
            "descripcion": "Compra de materiales",
            "fecha":       "2025-06-01",
        })

        assert resultado["status"] == "ok"
        assert resultado["gasto"]["estado"] == "pendiente"
        assert resultado["gasto"]["monto"]  == 15000.00

    def test_falla_si_rol_contador(self, reload_module, sb):
        """Contador no puede crear gastos."""
        _mock_table(sb, data=PERFIL_CONTADOR)

        resultado = reload_module.crear_gasto({
            "user_id":     CONTADOR_ID,
            "monto":       5000,
            "descripcion": "X",
            "fecha":       "2025-06-01",
        })

        assert resultado["status"] == "error"
        assert "operario" in resultado["mensaje"].lower()

    def test_falla_si_monto_cero(self, reload_module, sb):
        """Monto igual a 0 debe ser rechazado."""
        _mock_table(sb, data=PERFIL_OPERARIO)

        resultado = reload_module.crear_gasto({
            "user_id":     OPERARIO_ID,
            "monto":       0,
            "descripcion": "Test",
            "fecha":       "2025-06-01",
        })

        assert resultado["status"] == "error"

    def test_falla_si_faltan_campos(self, reload_module, sb):
        """Sin descripción ni fecha debe fallar."""
        _mock_table(sb, data=PERFIL_OPERARIO)

        resultado = reload_module.crear_gasto({
            "user_id": OPERARIO_ID,
            "monto":   1000,
        })

        assert resultado["status"] == "error"
        assert "faltan" in resultado["mensaje"].lower()

    def test_acepta_comprobante_url_opcional(self, reload_module, sb):
        """comprobante_url es opcional, no debe fallar si no viene."""
        gasto_con_url = {**GASTO_PENDIENTE, "comprobante_url": "https://url.com/img.jpg"}

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.insert.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(
                data=PERFIL_OPERARIO if name == "profiles" else [gasto_con_url]
            )
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.crear_gasto({
            "user_id":        OPERARIO_ID,
            "monto":          5000,
            "descripcion":    "Test con url",
            "fecha":          "2025-06-01",
            "comprobante_url":"https://url.com/img.jpg",
        })

        assert resultado["status"] == "ok"


# ─────────────────────────────────────────────────────────
# TEST: listar_gastos
# ─────────────────────────────────────────────────────────

class TestListarGastos:

    def test_operario_ve_solo_los_suyos(self, reload_module, sb):
        """Verifica que la query filtra por operario_id cuando el rol es operario."""
        gastos = [GASTO_PENDIENTE]

        calls = []

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.side_effect = lambda k, v: (calls.append((k, v)), chain)[1]
            chain.gte.return_value     = chain
            chain.lte.return_value     = chain
            chain.order.return_value   = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(
                data=PERFIL_OPERARIO if name == "profiles" else gastos
            )
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.listar_gastos({
            "user_id": OPERARIO_ID,
            "filtros": {},
        })

        assert resultado["status"] == "ok"
        assert resultado["total"] == 1
        # Debe haber filtrado por operario_id
        assert any(k == "operario_id" for k, _ in calls)

    def test_contador_ve_todos(self, reload_module, sb):
        """Contador no debe tener filtro por operario_id."""
        gastos = [GASTO_PENDIENTE, {**GASTO_PENDIENTE, "id": "otro-gasto"}]

        calls = []

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.side_effect = lambda k, v: (calls.append((k, v)), chain)[1]
            chain.gte.return_value    = chain
            chain.lte.return_value    = chain
            chain.order.return_value  = chain
            chain.single.return_value = chain
            chain.execute.return_value = MagicMock(
                data=PERFIL_CONTADOR if name == "profiles" else gastos
            )
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.listar_gastos({
            "user_id": CONTADOR_ID,
            "filtros": {},
        })

        assert resultado["status"] == "ok"
        assert resultado["total"] == 2
        # NO debe filtrar por operario_id
        assert not any(k == "operario_id" for k, _ in calls)

    def test_filtro_por_estado(self, reload_module, sb):
        """El filtro estado debe agregarse a la query."""
        calls = []

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.side_effect = lambda k, v: (calls.append((k, v)), chain)[1]
            chain.gte.return_value    = chain
            chain.lte.return_value    = chain
            chain.order.return_value  = chain
            chain.single.return_value = chain
            chain.execute.return_value = MagicMock(
                data=PERFIL_CONTADOR if name == "profiles" else [GASTO_PENDIENTE]
            )
            return chain

        sb.table.side_effect = table_side_effect

        reload_module.listar_gastos({
            "user_id": CONTADOR_ID,
            "filtros": {"estado": "pendiente"},
        })

        assert any(k == "estado" and v == "pendiente" for k, v in calls)

    def test_sin_permiso_tecnico(self, reload_module, sb):
        """Técnico no puede listar gastos."""
        perfil_tecnico = {**PERFIL_OPERARIO, "id": "tec-123", "rol": "tecnico"}
        _mock_table(sb, data=perfil_tecnico)

        resultado = reload_module.listar_gastos({"user_id": "tec-123", "filtros": {}})

        assert resultado["status"] == "error"


# ─────────────────────────────────────────────────────────
# TEST: obtener_gasto
# ─────────────────────────────────────────────────────────

class TestObtenerGasto:

    def test_operario_ve_su_propio_gasto(self, reload_module, sb):
        responses = [PERFIL_OPERARIO, GASTO_PENDIENTE]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.obtener_gasto({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "ok"
        assert resultado["gasto"]["id"] == GASTO_ID

    def test_operario_no_ve_gasto_ajeno(self, reload_module, sb):
        """Operario distinto no puede ver el gasto."""
        gasto_ajeno = {**GASTO_PENDIENTE, "operario_id": "otro-operario"}

        responses = [PERFIL_OPERARIO, gasto_ajeno]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.obtener_gasto({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "permiso" in resultado["mensaje"].lower()

    def test_gasto_no_encontrado(self, reload_module, sb):
        responses = [PERFIL_OPERARIO, None]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.obtener_gasto({
            "user_id":  OPERARIO_ID,
            "gasto_id": "no-existe",
        })

        assert resultado["status"] == "error"
        assert "no encontrado" in resultado["mensaje"].lower()


# ─────────────────────────────────────────────────────────
# TEST: aprobar_gasto
# ─────────────────────────────────────────────────────────

class TestAprobarGasto:

    def test_contador_aprueba_pendiente(self, reload_module, sb):
        gasto_aprobado = {**GASTO_PENDIENTE, "estado": "aprobado", "contador_id": CONTADOR_ID}
        responses = [PERFIL_CONTADOR, {"estado": "pendiente"}, gasto_aprobado]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.update.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 2)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.aprobar_gasto({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "ok"
        assert resultado["gasto"]["estado"] == "aprobado"

    def test_no_se_puede_aprobar_ya_aprobado(self, reload_module, sb):
        """Un gasto ya aprobado no puede aprobarse de nuevo."""
        responses = [PERFIL_CONTADOR, {"estado": "aprobado"}]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.aprobar_gasto({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "aprobado" in resultado["mensaje"].lower()

    def test_operario_no_puede_aprobar(self, reload_module, sb):
        _mock_table(sb, data=PERFIL_OPERARIO)

        resultado = reload_module.aprobar_gasto({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "contador" in resultado["mensaje"].lower()


# ─────────────────────────────────────────────────────────
# TEST: rechazar_gasto
# ─────────────────────────────────────────────────────────

class TestRechazarGasto:

    def test_contador_rechaza_con_motivo(self, reload_module, sb):
        gasto_rechazado = {**GASTO_PENDIENTE, "estado": "rechazado", "motivo_rechazo": "Comprobante ilegible"}
        responses = [PERFIL_CONTADOR, {"estado": "pendiente"}, gasto_rechazado]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.update.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 2)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.rechazar_gasto({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
            "motivo":   "Comprobante ilegible",
        })

        assert resultado["status"] == "ok"
        assert resultado["gasto"]["estado"] == "rechazado"
        assert resultado["gasto"]["motivo_rechazo"] == "Comprobante ilegible"

    def test_falla_sin_motivo(self, reload_module, sb):
        """El motivo es obligatorio para rechazar."""
        _mock_table(sb, data=PERFIL_CONTADOR)

        resultado = reload_module.rechazar_gasto({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
            "motivo":   "",
        })

        assert resultado["status"] == "error"
        assert "motivo" in resultado["mensaje"].lower()

    def test_no_se_puede_rechazar_ya_rechazado(self, reload_module, sb):
        responses = [PERFIL_CONTADOR, {"estado": "rechazado"}]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.rechazar_gasto({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
            "motivo":   "Algo",
        })

        assert resultado["status"] == "error"


# ─────────────────────────────────────────────────────────
# TEST: eliminar_gasto
# ─────────────────────────────────────────────────────────

class TestEliminarGasto:

    def test_operario_elimina_su_gasto_pendiente(self, reload_module, sb):
        responses = [PERFIL_OPERARIO, GASTO_PENDIENTE]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.delete.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.eliminar_gasto({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "ok"
        assert "eliminado" in resultado["mensaje"].lower()

    def test_no_puede_eliminar_aprobado(self, reload_module, sb):
        gasto_aprobado = {**GASTO_PENDIENTE, "estado": "aprobado"}
        responses = [PERFIL_OPERARIO, gasto_aprobado]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.eliminar_gasto({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "revisado" in resultado["mensaje"].lower()

    def test_no_puede_eliminar_gasto_ajeno(self, reload_module, sb):
        gasto_ajeno = {**GASTO_PENDIENTE, "operario_id": "otro-operario"}
        responses = [PERFIL_OPERARIO, gasto_ajeno]
        idx = [0]

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value  = chain
            chain.eq.return_value      = chain
            chain.single.return_value  = chain
            chain.execute.return_value = MagicMock(data=responses[min(idx[0], 1)])
            idx[0] += 1
            return chain

        sb.table.side_effect = table_side_effect

        resultado = reload_module.eliminar_gasto({
            "user_id":  OPERARIO_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "permiso" in resultado["mensaje"].lower()

    def test_contador_no_puede_eliminar(self, reload_module, sb):
        _mock_table(sb, data=PERFIL_CONTADOR)

        resultado = reload_module.eliminar_gasto({
            "user_id":  CONTADOR_ID,
            "gasto_id": GASTO_ID,
        })

        assert resultado["status"] == "error"
        assert "operario" in resultado["mensaje"].lower()
