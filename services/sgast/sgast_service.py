import json
import time
import os
from bus.soa_lib import connect_to_bus, send_message, receive_message
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]  # service_role bypasea RLS

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
SERVICE_NAME = "sgast"
TEST_TOKEN = "test-token-123"


# ─────────────────────────────────────────────
# RESPUESTAS DEL BUS
# ─────────────────────────────────────────────

def esperar_respuesta(sock, esperado_reply_to: str, timeout=10):
    start = time.time()

    while time.time() - start < timeout:
        resp = receive_message(sock)
        if not resp:
            continue

        try:
            data = json.loads(resp[5:].decode())

            if data.get("reply_to") == esperado_reply_to:
                return data

        except Exception:
            continue

    return None


# ─────────────────────────────────────────────
# AUTH CON SAUTH
# ─────────────────────────────────────────────

def verificar_token(sock, token: str) -> dict:
    request = {
        "op": "verify",
        "token": token,
        "reply_to": SERVICE_NAME
    }

    send_message(sock, "sauth", json.dumps(request))

    respuesta = esperar_respuesta(sock, SERVICE_NAME)

    if not respuesta:
        return {"status": "error", "mensaje": "sauth no respondió"}

    return respuesta


def ping_test(sock) -> dict:
    print("[sgast] enviando verify con TEST_TOKEN...")
    return verificar_token(sock, TEST_TOKEN)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_perfil(user_id: str) -> dict | None:
    """Devuelve el perfil del usuario o None si no existe."""
    res = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data


def _require_rol(user_id: str, roles: list[str]) -> dict | None:
    """
    Verifica que el usuario tenga uno de los roles dados.
    Retorna el perfil si OK, None si no tiene permiso.
    """
    perfil = _get_perfil(user_id)
    if not perfil or perfil.get("rol") not in roles:
        return None
    return perfil
def _first_result(data):
    """
    Compatibilidad entre Supabase real y mocks de pytest.
    Si viene una lista devuelve el primer elemento.
    Si viene un dict devuelve el dict.
    """
    if isinstance(data, list):
        return data[0] if data else None
    return data

# ─────────────────────────────────────────────
# OPERACIONES DE GASTOS
# ─────────────────────────────────────────────

def crear_gasto(payload: dict) -> dict:
    """
    Crea un nuevo gasto en estado 'pendiente'.
    Rol requerido: operario.

    payload: {
        "op": "crear_gasto",
        "token": "...",
        "user_id": "uuid",
        "monto": 15000.00,
        "descripcion": "Compra de materiales",
        "fecha": "2025-06-01",          # ISO date
        "comprobante_url": "https://..."  # opcional
    }
    """
    user_id = payload.get("user_id")
    perfil  = _require_rol(user_id, ["operario"])
    if not perfil:
        return {"status": "error", "mensaje": "Solo operarios pueden crear gastos"}

    monto       = payload.get("monto")
    descripcion = payload.get("descripcion", "").strip()
    fecha       = payload.get("fecha")

    if not all([monto, descripcion, fecha]):
        return {"status": "error", "mensaje": "Faltan campos: monto, descripcion, fecha"}
    if float(monto) <= 0:
        return {"status": "error", "mensaje": "El monto debe ser mayor a 0"}

    nuevo = {
        "operario_id":     user_id,
        "monto":           float(monto),
        "descripcion":     descripcion,
        "fecha":           fecha,
        "estado":          "pendiente",
        "comprobante_url": payload.get("comprobante_url"),  # None si no viene
    }

    res = supabase.table("gastos").insert(nuevo).execute()

    if not res.data:
        return {"status": "error", "mensaje": "Error al insertar en base de datos"}

    return {"status": "ok", "gasto": res.data[0]}


def listar_gastos(payload: dict) -> dict:
    """
    Lista gastos con filtros opcionales.
    Operario ve solo los suyos. Contador ve todos.

    payload: {
        "op": "listar_gastos",
        "user_id": "uuid",
        "filtros": {                  # todos opcionales
            "estado": "pendiente",    # pendiente | aprobado | rechazado
            "desde":  "2025-01-01",   # fecha ISO
            "hasta":  "2025-12-31"
        }
    }
    """
    user_id = payload.get("user_id")
    perfil  = _require_rol(user_id, ["operario", "contador"])
    if not perfil:
        return {"status": "error", "mensaje": "Sin permiso para listar gastos"}

    filtros = payload.get("filtros", {})
    query   = supabase.table("gastos").select("*")

    # Operario solo ve los suyos
    if perfil["rol"] == "operario":
        query = query.eq("operario_id", user_id)

    if filtros.get("estado"):
        query = query.eq("estado", filtros["estado"])
    if filtros.get("desde"):
        query = query.gte("fecha", filtros["desde"])
    if filtros.get("hasta"):
        query = query.lte("fecha", filtros["hasta"])

    query = query.order("created_at", desc=True)
    res   = query.execute()

    return {"status": "ok", "gastos": res.data or [], "total": len(res.data or [])}


def obtener_gasto(payload: dict) -> dict:
    """
    Obtiene un gasto por ID.
    Operario solo puede ver los suyos. Contador ve cualquiera.

    payload: { "op": "obtener_gasto", "user_id": "uuid", "gasto_id": "uuid" }
    """
    user_id  = payload.get("user_id")
    gasto_id = payload.get("gasto_id")
    perfil   = _require_rol(user_id, ["operario", "contador"])

    if not perfil:
        return {"status": "error", "mensaje": "Sin permiso"}
    if not gasto_id:
        return {"status": "error", "mensaje": "Falta gasto_id"}

    res = supabase.table("gastos").select("*").eq("id", gasto_id).single().execute()

    if not res.data:
        return {"status": "error", "mensaje": "Gasto no encontrado"}

    gasto = res.data

    # Operario no puede ver gastos de otros
    if perfil["rol"] == "operario" and gasto["operario_id"] != user_id:
        return {"status": "error", "mensaje": "Sin permiso para ver este gasto"}

    return {"status": "ok", "gasto": gasto}


def aprobar_gasto(payload: dict) -> dict:
    """
    Aprueba un gasto pendiente.
    Rol requerido: contador.

    payload: { "op": "aprobar_gasto", "user_id": "uuid", "gasto_id": "uuid" }
    """
    user_id = payload.get("user_id")
    gasto_id = payload.get("gasto_id")
    perfil = _require_rol(user_id, ["contador"])

    if not perfil:
        return {"status": "error", "mensaje": "Solo contadores pueden aprobar gastos"}

    if not gasto_id:
        return {"status": "error", "mensaje": "Falta gasto_id"}

    res = (
        supabase.table("gastos")
        .select("estado")
        .eq("id", gasto_id)
        .single()
        .execute()
    )

    if not res.data:
        return {"status": "error", "mensaje": "Gasto no encontrado"}

    if res.data["estado"] != "pendiente":
        return {
            "status": "error",
            "mensaje": f"El gasto ya está {res.data['estado']}"
        }

    from datetime import datetime, timezone

    update = {
        "estado": "aprobado",
        "contador_id": user_id,
        "fecha_revision": datetime.now(timezone.utc).isoformat(),
        "motivo_rechazo": None,
    }

    res = (
        supabase.table("gastos")
        .update(update)
        .eq("id", gasto_id)
        .execute()
    )

    gasto = _first_result(res.data)

    return {
        "status": "ok",
        "gasto": gasto,
    }


def rechazar_gasto(payload: dict) -> dict:
    """
    Rechaza un gasto pendiente con un motivo obligatorio.
    Rol requerido: contador.
    """
    user_id = payload.get("user_id")
    gasto_id = payload.get("gasto_id")
    motivo = payload.get("motivo", "").strip()

    perfil = _require_rol(user_id, ["contador"])

    if not perfil:
        return {"status": "error", "mensaje": "Solo contadores pueden rechazar gastos"}

    if not gasto_id:
        return {"status": "error", "mensaje": "Falta gasto_id"}

    if not motivo:
        return {
            "status": "error",
            "mensaje": "El motivo de rechazo es obligatorio"
        }

    res = (
        supabase.table("gastos")
        .select("estado")
        .eq("id", gasto_id)
        .single()
        .execute()
    )

    if not res.data:
        return {"status": "error", "mensaje": "Gasto no encontrado"}

    if res.data["estado"] != "pendiente":
        return {
            "status": "error",
            "mensaje": f"El gasto ya está {res.data['estado']}"
        }

    from datetime import datetime, timezone

    update = {
        "estado": "rechazado",
        "contador_id": user_id,
        "fecha_revision": datetime.now(timezone.utc).isoformat(),
        "motivo_rechazo": motivo,
    }

    res = (
        supabase.table("gastos")
        .update(update)
        .eq("id", gasto_id)
        .execute()
    )

    gasto = _first_result(res.data)

    return {
        "status": "ok",
        "gasto": gasto,
    }


def eliminar_gasto(payload: dict) -> dict:
    """
    Elimina un gasto solo si está en estado 'pendiente' y pertenece al operario.

    payload: { "op": "eliminar_gasto", "user_id": "uuid", "gasto_id": "uuid" }
    """
    user_id  = payload.get("user_id")
    gasto_id = payload.get("gasto_id")
    perfil   = _require_rol(user_id, ["operario"])

    if not perfil:
        return {"status": "error", "mensaje": "Solo operarios pueden eliminar sus gastos"}

    res = supabase.table("gastos").select("*").eq("id", gasto_id).single().execute()
    if not res.data:
        return {"status": "error", "mensaje": "Gasto no encontrado"}

    gasto = res.data
    if gasto["operario_id"] != user_id:
        return {
            "status": "error",
            "mensaje": "Sin permiso para eliminar gastos de otros usuarios"
        }
    if gasto["estado"] != "pendiente":
        return {"status": "error", "mensaje": "No se puede eliminar un gasto ya revisado"}

    supabase.table("gastos").delete().eq("id", gasto_id).execute()
    return {"status": "ok", "mensaje": "Gasto eliminado"}
# ─────────────────────────────────────────────
# LOGICA GASTOS (BASE)
# ─────────────────────────────────────────────

def procesar_mensaje(sock, raw_payload: str) -> dict:
    try:
        payload = json.loads(raw_payload)
        op = payload.get("op")

        if op == "ping_test":
            return ping_test(sock)
        if op == "verificar_token":
            token = payload.get("token", TEST_TOKEN)
            return verificar_token(sock, token)

        # ── Gastos ──────────────────────────────
        if op == "crear_gasto":
            return crear_gasto(payload)
        if op == "listar_gastos":
            return listar_gastos(payload)
        if op == "obtener_gasto":
            return obtener_gasto(payload)
        if op == "aprobar_gasto":
            return aprobar_gasto(payload)
        if op == "rechazar_gasto":
            return rechazar_gasto(payload)
        if op == "eliminar_gasto":
            return eliminar_gasto(payload)

        return {"status": "error", "mensaje": f"op '{op}' no soportada"}

    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    sock = connect_to_bus()

    print("[sgast] registrando...")
    send_message(sock, "sinit", SERVICE_NAME)
    receive_message(sock)

    print("[sgast] listo y escuchando")

    # ─────────────────────────────────────────────
    # ⏳ CUENTA REGRESIVA
    # ─────────────────────────────────────────────
    print("[sgast] preparando test con sauth...")

    for i in range(3, 0, -1):
        print(f"[sgast] enviando test en {i}...")
        time.sleep(1)

    # ─────────────────────────────────────────────
    # TEST INICIAL AUTH
    # ─────────────────────────────────────────────
    print("[sgast] test inicial con sauth...")

    send_message(sock, "sauth", json.dumps({
        "op": "ping",
        "reply_to": SERVICE_NAME
    }))

    resp = esperar_respuesta(sock, SERVICE_NAME)

    print("[sgast] respuesta sauth test:", resp)

    # ─────────────────────────────────────────────
    # LOOP PRINCIPAL
    # ─────────────────────────────────────────────
    while True:
        print("[sgast] esperando mensajes...")

        data = receive_message(sock)

        if not data:
            print("[sgast] conexión cerrada")
            break

        raw_payload = data[5:].decode()
        print(f"[sgast] recibido: {raw_payload}")

        respuesta = procesar_mensaje(sock, raw_payload)

        # 🔥 reply_to dinámico
        try:
            req = json.loads(raw_payload)
            destino = req.get("reply_to", SERVICE_NAME)
        except:
            destino = SERVICE_NAME

        send_message(sock, destino, json.dumps(respuesta, ensure_ascii=False))
        print(f"[sgast] enviado: {respuesta}")


if __name__ == "__main__":
    main()