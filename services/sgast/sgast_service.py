"""
Servicio de Gastos — SCG
Nombre en el bus: "sgast"   (exactamente 5 caracteres)

TODO: Implementar operaciones de Gastos.
"""
import json
import os
from supabase import create_client
from soa_lib import connect_to_bus, send_message, receive_message

SERVICE_NAME  = "sgast"
SUPABASE_URL  = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY  = os.getenv("SUPABASE_KEY", "")


def procesar_mensaje(raw_payload: str) -> dict:
    try:
        payload = json.loads(raw_payload)
        op = payload.get("op")
        return {"status": "error", "mensaje": f"Operación '{op}' aún no implementada"}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def main():
    sock = connect_to_bus()
    try:
        print(f"[sgast] Registrando servicio 'sgast'...")
        send_message(sock, "sinit", SERVICE_NAME)
        confirmacion = receive_message(sock)
        print(f"[sgast] Bus confirmó: {confirmacion!r}")
        print(f"[sgast] Listo.\n")

        while True:
            data = receive_message(sock)
            if not data:
                print(f"[sgast] Bus cerró la conexión.")
                break
            raw_payload = data[5:].decode("utf-8")
            print(f"[sgast] Mensaje recibido: {raw_payload}")
            respuesta = procesar_mensaje(raw_payload)
            send_message(sock, SERVICE_NAME, json.dumps(respuesta))
            print(f"[sgast] Respuesta enviada: {respuesta}\n")
    except KeyboardInterrupt:
        print(f"\n[sgast] Detenido.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
