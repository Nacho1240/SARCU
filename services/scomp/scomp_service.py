import json
import time
from soa_lib import connect_to_bus, send_message, receive_message
import os
import uuid as uuid_lib
from supabase import create_client
SERVICE_NAME = "scomp"

TEST_TOKEN = "test-token-123"
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET = "comprobantes"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_perfil(user_id: str) -> dict | None:
    res = supabase.table("profiles").select("rol").eq("id", user_id).single().execute()
    return res.data


# ─────────────────────────────────────────────
# OPERACIONES DE COMPROBANTES
# ─────────────────────────────────────────────

def subir_comprobante(payload: dict) -> dict:
    """
    Sube un archivo al bucket y devuelve la URL pública.
    El frontend ya subió el archivo; aquí solo se registra la URL
    y opcionalmente se vincula al gasto.

    Si el frontend usa Supabase Storage directamente (recomendado),
    este endpoint solo persiste la URL en el gasto.

    payload: {
        "op": "subir_comprobante",
        "user_id": "uuid",
        "gasto_id": "uuid",
        "url": "https://...supabase.co/storage/v1/object/public/comprobantes/..."
    }
    """
    user_id  = payload.get("user_id")
    gasto_id = payload.get("gasto_id")
    url      = payload.get("url", "").strip()

    perfil = _get_perfil(user_id)
    if not perfil or perfil["rol"] not in ("operario",):
        return {"status": "error", "mensaje": "Solo operarios pueden subir comprobantes"}
    if not gasto_id or not url:
        return {"status": "error", "mensaje": "Faltan campos: gasto_id, url"}

    # Verificar que el gasto pertenece al operario y está pendiente
    res = supabase.table("gastos").select("operario_id,estado").eq("id", gasto_id).single().execute()
    if not res.data:
        return {"status": "error", "mensaje": "Gasto no encontrado"}

    gasto = res.data
    if gasto["operario_id"] != user_id:
        return {"status": "error", "mensaje": "No tienes permiso sobre este gasto"}
    if gasto["estado"] != "pendiente":
        return {"status": "error", "mensaje": "Solo se puede adjuntar a gastos pendientes"}

    # Actualizar URL en la tabla gastos
    supabase.table("gastos").update({"comprobante_url": url}).eq("id", gasto_id).execute()

    return {"status": "ok", "url": url, "gasto_id": gasto_id}


def obtener_url(payload: dict) -> dict:
    """
    Devuelve la URL pública del comprobante de un gasto.
    Cualquier rol autenticado puede acceder.

    payload: { "op": "obtener_url", "user_id": "uuid", "gasto_id": "uuid" }
    """
    user_id  = payload.get("user_id")
    gasto_id = payload.get("gasto_id")

    if not _get_perfil(user_id):
        return {"status": "error", "mensaje": "Usuario no encontrado"}

    res = supabase.table("gastos").select("comprobante_url,estado").eq("id", gasto_id).single().execute()
    if not res.data:
        return {"status": "error", "mensaje": "Gasto no encontrado"}

    url = res.data.get("comprobante_url")
    if not url:
        return {"status": "error", "mensaje": "Este gasto no tiene comprobante adjunto"}

    return {"status": "ok", "url": url}


def vincular_comprobante(payload: dict) -> dict:
    """
    Vincula manualmente una URL ya existente en Storage a un gasto.
    Útil si el frontend sube directo a Supabase y luego notifica al bus.

    payload: {
        "op": "vincular_comprobante",
        "user_id": "uuid",
        "gasto_id": "uuid",
        "url": "https://..."
    }
    """
    # Reutiliza la misma lógica que subir_comprobante
    return subir_comprobante(payload)


def eliminar_comprobante(payload: dict) -> dict:
    """
    Elimina el comprobante del bucket y limpia la URL en el gasto.
    Solo el operario dueño puede hacerlo, y solo si el gasto está pendiente.

    payload: {
        "op": "eliminar_comprobante",
        "user_id": "uuid",
        "gasto_id": "uuid"
    }
    """
    user_id  = payload.get("user_id")
    gasto_id = payload.get("gasto_id")

    perfil = _get_perfil(user_id)
    if not perfil or perfil["rol"] != "operario":
        return {"status": "error", "mensaje": "Solo operarios pueden eliminar comprobantes"}

    res = supabase.table("gastos").select("operario_id,estado,comprobante_url").eq("id", gasto_id).single().execute()
    if not res.data:
        return {"status": "error", "mensaje": "Gasto no encontrado"}

    gasto = res.data
    if gasto["operario_id"] != user_id:
        return {"status": "error", "mensaje": "No tienes permiso sobre este gasto"}
    if gasto["estado"] != "pendiente":
        return {"status": "error", "mensaje": "No se puede modificar un gasto ya revisado"}

    url = gasto.get("comprobante_url")
    if not url:
        return {"status": "error", "mensaje": "Este gasto no tiene comprobante"}

    # Extraer la ruta relativa del bucket desde la URL pública
    # URL pública: https://<project>.supabase.co/storage/v1/object/public/comprobantes/<path>
    try:
        path = url.split(f"/object/public/{BUCKET}/")[-1]
        supabase.storage.from_(BUCKET).remove([path])
    except Exception as e:
        return {"status": "error", "mensaje": f"Error al eliminar del storage: {e}"}

    # Limpiar URL en la tabla
    supabase.table("gastos").update({"comprobante_url": None}).eq("id", gasto_id).execute()

    return {"status": "ok", "mensaje": "Comprobante eliminado"}

def esperar_respuesta(sock, esperado_reply_to: str, timeout=10):
    start = time.time()

    while True:
        if time.time() - start > timeout:
            return None

        resp = receive_message(sock)
        if not resp:
            continue

        try:
            data = json.loads(resp[5:].decode())

            if data.get("reply_to") == esperado_reply_to:
                return data

        except Exception:
            continue


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
    print("[scomp] enviando verify con TEST_TOKEN...")
    return verificar_token(sock, TEST_TOKEN)


def procesar_mensaje(sock, raw_payload: str) -> dict:
    try:
        payload = json.loads(raw_payload)
        op = payload.get("op")

        if op == "ping_test":
            return ping_test(sock)
        if op == "verificar_token":
            token = payload.get("token", TEST_TOKEN)
            return verificar_token(sock, token)

        # ── Comprobantes ─────────────────────────
        if op == "subir_comprobante":
            return subir_comprobante(payload)
        if op == "obtener_url":
            return obtener_url(payload)
        if op == "vincular_comprobante":
            return vincular_comprobante(payload)
        if op == "eliminar_comprobante":
            return eliminar_comprobante(payload)

        return {"status": "error", "mensaje": f"op '{op}' no soportada"}

    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def main():
    sock = connect_to_bus()

    print("[scomp] registrando...")
    send_message(sock, "sinit", SERVICE_NAME)
    receive_message(sock)

    print("[scomp] listo y escuchando")

    # ─────────────────────────────────────────────
    # ⏳ CUENTA REGRESIVA SIMPLE
    # ─────────────────────────────────────────────
    print("[scomp] preparando test con sauth...")

    for i in range(3, 0, -1):
        print(f"[scomp] enviando test en {i}...")
        time.sleep(1)

    # ─────────────────────────────────────────────
    # TEST INICIAL
    # ─────────────────────────────────────────────
    print("[scomp] test inicial con sauth...")

    send_message(sock, "sauth", json.dumps({
        "op": "ping",
        "reply_to": SERVICE_NAME
    }))

    resp = esperar_respuesta(sock, SERVICE_NAME)

    print("[scomp] respuesta sauth test:", resp)

    # ─────────────────────────────────────────────
    # LOOP PRINCIPAL
    # ─────────────────────────────────────────────
    while True:
        print("[scomp] esperando mensajes...")

        data = receive_message(sock)

        if not data:
            print("[scomp] conexión cerrada")
            break

        raw_payload = data[5:].decode()
        print(f"[scomp] recibido: {raw_payload}")

        respuesta = procesar_mensaje(sock, raw_payload)

        send_message(sock, SERVICE_NAME, json.dumps(respuesta))
        print(f"[scomp] enviado: {respuesta}")


if __name__ == "__main__":
    main()