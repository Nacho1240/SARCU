"""
Servicio de Reportes — SCG
Nombre en el bus: "srept"   (exactamente 5 caracteres)

TODO: Implementar operaciones de Reportes.
"""
import json
import os
from supabase import create_client
from soa_lib import connect_to_bus, send_message, receive_message

SERVICE_NAME  = "srept"
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
        print(f"[srept] Registrando servicio 'srept'...")
        send_message(sock, "sinit", SERVICE_NAME)
        confirmacion = receive_message(sock)
        print(f"[srept] Bus confirmó: {confirmacion!r}")
        print(f"[srept] Listo.\n")

        while True:
            data = receive_message(sock)
            if not data:
                print(f"[srept] Bus cerró la conexión.")
                break
            raw_payload = data[5:].decode("utf-8")
            print(f"[srept] Mensaje recibido: {raw_payload}")
            respuesta = procesar_mensaje(raw_payload)
            send_message(sock, SERVICE_NAME, json.dumps(respuesta))
            print(f"[srept] Respuesta enviada: {respuesta}\n")
    except KeyboardInterrupt:
        print(f"\n[srept] Detenido.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
