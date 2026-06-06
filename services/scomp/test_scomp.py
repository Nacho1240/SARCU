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
# FIXTURES DE DEBUG
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def log_test(request):
    print("\n")
    print("=" * 100)
    print(f"INICIO TEST -> {request.node.name}")
    print("=" * 100)

    yield

    print(f"FIN TEST -> {request.node.name}")
    print("=" * 100)


def debug_result(nombre, payload=None, resultado=None):
    print("\n--- DEBUG RESULTADO -------------------------")

    if nombre:
        print("TEST:")
        print(nombre)

    if payload is not None:
        print("\nPAYLOAD:")
        print(payload)

    if resultado is not None:
        print("\nRESULTADO:")
        print(resultado)

    print("---------------------------------------------\n")


# ─────────────────────────────────────────────
# FIXTURES DE SUPABASE MOCKEADO
# ─────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mostrar_resultado_test(request):

    yield

    print(
        f"\n[TEST FINALIZADO] {request.node.name}"
    )
@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    mock_client = MagicMock()

    monkeypatch.setenv(
        "SUPABASE_URL",
        "https://fake.supabase.co"
    )

    monkeypatch.setenv(
        "SUPABASE_KEY",
        "fake-service-key"
    )

    with patch(
        "supabase.create_client",
        return_value=mock_client
    ):
        yield mock_client


@pytest.fixture
def sb(mock_supabase):
    return mock_supabase


@pytest.fixture(autouse=True)
def reload_module(mock_supabase):
    import sys

    if "scomp_service" in sys.modules:
        del sys.modules["scomp_service"]

    with patch(
        "supabase.create_client",
        return_value=mock_supabase
    ):
        import scomp_service

        print("\n[DEBUG] scomp_service recargado")

        yield scomp_service


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def ejecutar_y_mostrar(nombre, funcion, payload):

    print("\n")
    print("=" * 80)
    print(f"EJECUTANDO: {nombre}")
    print("=" * 80)

    print("\nPAYLOAD:")
    print(payload)

    resultado = funcion(payload)

    print("\nRESULTADO:")
    print(resultado)

    print("=" * 80)

    return resultado
def _build_chain(sb, responses_by_table):
    """
    Mock de Supabase extremadamente verboso para seguir
    todo el flujo del servicio paso a paso.
    """

    def table_side_effect(table_name):

        print("\n" + "-" * 80)
        print(f"[SUPABASE] table('{table_name}')")
        print("-" * 80)

        data = responses_by_table.get(table_name)

        chain = MagicMock()

        # --------------------------------------------------
        # SELECT
        # --------------------------------------------------
        def select_side_effect(*args, **kwargs):
            print(
                f"[SUPABASE] {table_name}.select("
                f"args={args}, kwargs={kwargs})"
            )
            return chain

        chain.select.side_effect = select_side_effect

        # --------------------------------------------------
        # UPDATE
        # --------------------------------------------------
        def update_side_effect(*args, **kwargs):
            print(
                f"[SUPABASE] {table_name}.update("
                f"args={args}, kwargs={kwargs})"
            )
            return chain

        chain.update.side_effect = update_side_effect

        # --------------------------------------------------
        # INSERT
        # --------------------------------------------------
        def insert_side_effect(*args, **kwargs):
            print(
                f"[SUPABASE] {table_name}.insert("
                f"args={args}, kwargs={kwargs})"
            )
            return chain

        chain.insert.side_effect = insert_side_effect

        # --------------------------------------------------
        # DELETE
        # --------------------------------------------------
        def delete_side_effect(*args, **kwargs):
            print(
                f"[SUPABASE] {table_name}.delete("
                f"args={args}, kwargs={kwargs})"
            )
            return chain

        chain.delete.side_effect = delete_side_effect

        # --------------------------------------------------
        # EQ
        # --------------------------------------------------
        def eq_side_effect(*args, **kwargs):
            print(
                f"[SUPABASE] {table_name}.eq("
                f"args={args}, kwargs={kwargs})"
            )
            return chain

        chain.eq.side_effect = eq_side_effect

        # --------------------------------------------------
        # SINGLE
        # --------------------------------------------------
        def single_side_effect(*args, **kwargs):
            print(
                f"[SUPABASE] {table_name}.single("
                f"args={args}, kwargs={kwargs})"
            )
            return chain

        chain.single.side_effect = single_side_effect

        # --------------------------------------------------
        # EXECUTE
        # --------------------------------------------------
        def execute_side_effect():

            print(
                f"[SUPABASE] {table_name}.execute()"
            )

            print(
                f"[SUPABASE] RESULTADO DEVUELTO:"
            )

            print(data)

            return MagicMock(data=data)

        chain.execute.side_effect = execute_side_effect

        return chain

    sb.table.side_effect = table_side_effect

    print("\n[MOCK CONFIGURADO]")

    for tabla, valor in responses_by_table.items():
        print(f"  {tabla}:")
        print(f"      {valor}")

    print()


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

# ─────────────────────────────────────────────────────────
# TEST: subir_comprobante
# ─────────────────────────────────────────────────────────

class TestSubirComprobante:

    def test_operario_vincula_url_correctamente(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_PENDIENTE,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url": URL_PUBLICA,
        }

        resultado = ejecutar_y_mostrar(
            "subir_comprobante",
            reload_module.subir_comprobante,
            payload
        )

        assert resultado["status"] == "ok"
        assert resultado["url"] == URL_PUBLICA
        assert resultado["gasto_id"] == GASTO_ID

    def test_contador_no_puede_subir(self, reload_module, sb):
        _build_chain(sb, {"profiles": PERFIL_CONTADOR})

        payload = {
            "user_id": CONTADOR_ID,
            "gasto_id": GASTO_ID,
            "url": URL_PUBLICA,
        }

        resultado = ejecutar_y_mostrar(
            "subir_comprobante",
            reload_module.subir_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "operario" in resultado["mensaje"].lower()

    def test_falla_sin_url(self, reload_module, sb):
        _build_chain(sb, {"profiles": PERFIL_OPERARIO})

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url": "",
        }

        resultado = ejecutar_y_mostrar(
            "subir_comprobante",
            reload_module.subir_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "faltan" in resultado["mensaje"].lower()

    def test_falla_sin_gasto_id(self, reload_module, sb):
        _build_chain(sb, {"profiles": PERFIL_OPERARIO})

        payload = {
            "user_id": OPERARIO_ID,
            "url": URL_PUBLICA,
        }

        resultado = ejecutar_y_mostrar(
            "subir_comprobante",
            reload_module.subir_comprobante,
            payload
        )

        assert resultado["status"] == "error"

    def test_falla_en_gasto_ajeno(self, reload_module, sb):
        gasto_ajeno = {
            **GASTO_PENDIENTE,
            "operario_id": "otro-operario"
        }

        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": gasto_ajeno,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url": URL_PUBLICA,
        }

        resultado = ejecutar_y_mostrar(
            "subir_comprobante",
            reload_module.subir_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "permiso" in resultado["mensaje"].lower()

    def test_falla_en_gasto_aprobado(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_APROBADO,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url": URL_PUBLICA,
        }

        resultado = ejecutar_y_mostrar(
            "subir_comprobante",
            reload_module.subir_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "pendiente" in resultado["mensaje"].lower()


# ─────────────────────────────────────────────────────────
# TEST: obtener_url
# ─────────────────────────────────────────────────────────

class TestObtenerUrl:

    def test_devuelve_url_si_existe(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_CON_URL,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "obtener_url",
            reload_module.obtener_url,
            payload
        )

        assert resultado["status"] == "ok"
        assert resultado["url"] == URL_PUBLICA

    def test_falla_si_no_hay_comprobante(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_PENDIENTE,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "obtener_url",
            reload_module.obtener_url,
            payload
        )

        assert resultado["status"] == "error"
        assert "comprobante" in resultado["mensaje"].lower()

    def test_falla_si_gasto_no_existe(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": None,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": "no-existe",
        }

        resultado = ejecutar_y_mostrar(
            "obtener_url",
            reload_module.obtener_url,
            payload
        )

        assert resultado["status"] == "error"
        assert "no encontrado" in resultado["mensaje"].lower()

    def test_falla_si_usuario_no_existe(self, reload_module, sb):
        _build_chain(sb, {"profiles": None})

        payload = {
            "user_id": "usuario-fantasma",
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "obtener_url",
            reload_module.obtener_url,
            payload
        )

        assert resultado["status"] == "error"

    def test_contador_puede_obtener_url(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_CONTADOR,
            "gastos": GASTO_CON_URL,
        })

        payload = {
            "user_id": CONTADOR_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "obtener_url",
            reload_module.obtener_url,
            payload
        )

        assert resultado["status"] == "ok"
        assert resultado["url"] == URL_PUBLICA


# ─────────────────────────────────────────────────────────
# TEST: vincular_comprobante
# ─────────────────────────────────────────────────────────

class TestVincularComprobante:

    def test_vincular_es_equivalente_a_subir(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_PENDIENTE,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url": URL_PUBLICA,
        }

        resultado = ejecutar_y_mostrar(
            "vincular_comprobante",
            reload_module.vincular_comprobante,
            payload
        )

        assert resultado["status"] == "ok"
        assert resultado["url"] == URL_PUBLICA

    def test_vincular_falla_en_gasto_ajeno(self, reload_module, sb):
        gasto_ajeno = {
            **GASTO_PENDIENTE,
            "operario_id": "otro"
        }

        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": gasto_ajeno,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
            "url": URL_PUBLICA,
        }

        resultado = ejecutar_y_mostrar(
            "vincular_comprobante",
            reload_module.vincular_comprobante,
            payload
        )

        assert resultado["status"] == "error"


# ─────────────────────────────────────────────────────────
# TEST: eliminar_comprobante
# ─────────────────────────────────────────────────────────

class TestEliminarComprobante:

    def test_operario_elimina_comprobante_propio(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_CON_URL,
        })

        sb.storage.from_.return_value.remove.return_value = MagicMock()

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "eliminar_comprobante",
            reload_module.eliminar_comprobante,
            payload
        )

        assert resultado["status"] == "ok"
        assert "eliminado" in resultado["mensaje"].lower()

    def test_llama_a_storage_remove_con_ruta_correcta(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_CON_URL,
        })

        storage_mock = MagicMock()
        sb.storage.from_.return_value = storage_mock

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        ejecutar_y_mostrar(
            "eliminar_comprobante",
            reload_module.eliminar_comprobante,
            payload
        )

        storage_mock.remove.assert_called_once()

        ruta_llamada = storage_mock.remove.call_args[0][0][0]

        assert ruta_llamada == "2025/06/boleta.jpg"
        assert "comprobantes" not in ruta_llamada

    def test_falla_si_no_hay_comprobante(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_PENDIENTE,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "eliminar_comprobante",
            reload_module.eliminar_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "comprobante" in resultado["mensaje"].lower()

    def test_falla_en_gasto_aprobado(self, reload_module, sb):
        gasto_aprobado_con_url = {
            **GASTO_CON_URL,
            "estado": "aprobado"
        }

        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": gasto_aprobado_con_url,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "eliminar_comprobante",
            reload_module.eliminar_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "revisado" in resultado["mensaje"].lower()

    def test_falla_en_gasto_ajeno(self, reload_module, sb):
        gasto_ajeno = {
            **GASTO_CON_URL,
            "operario_id": "otro-operario"
        }

        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": gasto_ajeno,
        })

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "eliminar_comprobante",
            reload_module.eliminar_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "permiso" in resultado["mensaje"].lower()

    def test_contador_no_puede_eliminar(self, reload_module, sb):
        _build_chain(sb, {"profiles": PERFIL_CONTADOR})

        payload = {
            "user_id": CONTADOR_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "eliminar_comprobante",
            reload_module.eliminar_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "operario" in resultado["mensaje"].lower()

    def test_storage_error_devuelve_error_descriptivo(self, reload_module, sb):
        _build_chain(sb, {
            "profiles": PERFIL_OPERARIO,
            "gastos": GASTO_CON_URL,
        })

        sb.storage.from_.return_value.remove.side_effect = Exception(
            "Connection timeout"
        )

        payload = {
            "user_id": OPERARIO_ID,
            "gasto_id": GASTO_ID,
        }

        resultado = ejecutar_y_mostrar(
            "eliminar_comprobante",
            reload_module.eliminar_comprobante,
            payload
        )

        assert resultado["status"] == "error"
        assert "storage" in resultado["mensaje"].lower()