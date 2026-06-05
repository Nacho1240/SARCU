import json
import time
from soa_lib import connect_to_bus, send_message, receive_message

SERVICE_NAME = "scomp"

TEST_TOKEN = "test-token-123"


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

        return {
            "status": "error",
            "mensaje": f"op '{op}' no soportada"
        }

    except Exception as e:
        return {
            "status": "error",
            "mensaje": str(e)
        }


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