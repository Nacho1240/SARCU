"""
Servicio de Autenticación — SCG (Sistema de Control de Gastos)
Nombre en el bus: "sauth"  (exactamente 5 caracteres)

Operaciones que acepta (campo "op" en el JSON):
  - login   : autentica al usuario con email/password
  - verify  : verifica si un token JWT sigue vigente y devuelve el rol

Formato de mensaje entrante (payload JSON):
  login  → {"op": "login",  "email": "x@x.com", "password": "clave"}
  verify → {"op": "verify", "token": "eyJ..."}

Formato de respuesta JSON:
  éxito  → {"status": "ok",    "token": "eyJ...", "rol": "operario", "user_id": "uuid"}
  error  → {"status": "error", "mensaje": "Descripción del error"}
"""

import json
from supabase import create_client, Client
from soa_lib import connect_to_bus, send_message, receive_message

# ── Configuración ──────────────────────────────────────────────────────────────
SERVICE_NAME  = "sauth"          # SIEMPRE 5 caracteres
SUPABASE_URL  = "TU_SUPABASE_URL_AQUI"   # ej: https://xxxx.supabase.co
SUPABASE_KEY  = "TU_SUPABASE_ANON_KEY"  # clave anon o service_role


# ── Lógica de negocio ──────────────────────────────────────────────────────────

def get_supabase() -> Client:
    """Crea y devuelve el cliente de Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def op_login(payload: dict) -> dict:
    """
    Autentica al usuario con Supabase Auth y devuelve token + rol.
    El rol se obtiene de la tabla 'profiles' (que ya tienes en Supabase).
    """
    email    = payload.get("email", "").strip()
    password = payload.get("password", "")

    if not email or not password:
        return {"status": "error", "mensaje": "email y password son obligatorios"}

    try:
        sb = get_supabase()

        # 1. Autenticar contra Supabase Auth
        resp = sb.auth.sign_in_with_password({"email": email, "password": password})

        token   = resp.session.access_token
        user_id = resp.user.id

        # 2. Obtener el rol desde la tabla profiles
        perfil = (
            sb.table("profiles")
              .select("rol")
              .eq("id", user_id)
              .single()
              .execute()
        )
        rol = perfil.data.get("rol", "desconocido")

        return {
            "status":  "ok",
            "token":   token,
            "user_id": user_id,
            "email":   email,
            "rol":     rol,
        }

    except Exception as e:
        # Supabase lanza excepción si las credenciales son incorrectas
        return {"status": "error", "mensaje": f"Credenciales inválidas: {str(e)}"}


def op_verify(payload: dict) -> dict:
    """
    Verifica que un JWT siga siendo válido y devuelve el user_id y rol.
    Útil para que otros servicios validen tokens sin contactar Supabase ellos mismos.
    """
    token = payload.get("token", "")

    if not token:
        return {"status": "error", "mensaje": "token es obligatorio"}

    try:
        sb = get_supabase()

        # Obtener el usuario a partir del token
        resp = sb.auth.get_user(token)
        user_id = resp.user.id

        # Obtener rol
        perfil = (
            sb.table("profiles")
              .select("rol")
              .eq("id", user_id)
              .single()
              .execute()
        )
        rol = perfil.data.get("rol", "desconocido")

        return {
            "status":  "ok",
            "user_id": user_id,
            "rol":     rol,
        }

    except Exception as e:
        return {"status": "error", "mensaje": f"Token inválido o expirado: {str(e)}"}


# ── Dispatcher ─────────────────────────────────────────────────────────────────

OPERACIONES = {
    "login":  op_login,
    "verify": op_verify,
}

def procesar_mensaje(raw_payload: str) -> dict:
    """
    Parsea el JSON recibido y despacha a la función correspondiente.
    Siempre devuelve un dict (nunca lanza excepción al llamador).
    """
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {"status": "error", "mensaje": "El payload no es JSON válido"}

    op = payload.get("op")
    if op not in OPERACIONES:
        ops_validas = list(OPERACIONES.keys())
        return {"status": "error", "mensaje": f"Operación '{op}' desconocida. Válidas: {ops_validas}"}

    return OPERACIONES[op](payload)


# ── Main: conexión al bus y bucle principal ────────────────────────────────────

def main():
    sock = connect_to_bus()

    try:
        # Paso 1: registrarse en el bus
        print(f"[sauth] Registrando servicio '{SERVICE_NAME}' en el bus...")
        send_message(sock, "sinit", SERVICE_NAME)

        confirmacion = receive_message(sock)
        print(f"[sauth] Bus confirmó: {confirmacion!r}")
        print("[sauth] Listo para recibir mensajes.\n")

        # Paso 2: bucle de trabajo
        while True:
            data = receive_message(sock)
            if not data:
                print("[sauth] Bus cerró la conexión.")
                break

            # Los primeros 5 bytes son el nombre del servicio (lo ignoramos aquí)
            raw_payload = data[5:].decode("utf-8")
            print(f"[sauth] Mensaje recibido: {raw_payload}")

            respuesta = procesar_mensaje(raw_payload)
            respuesta_str = json.dumps(respuesta)

            send_message(sock, SERVICE_NAME, respuesta_str)
            print(f"[sauth] Respuesta enviada: {respuesta_str}\n")

    except KeyboardInterrupt:
        print("\n[sauth] Detenido por el usuario.")
    except Exception as e:
        print(f"[sauth] Error inesperado: {e}")
    finally:
        sock.close()
        print("[sauth] Socket cerrado.")


if __name__ == "__main__":
    main()
