"""
Servicio de Autenticación — SCG (Sistema de Control de Gastos)
Nombre en el bus: "sauth"  (exactamente 5 caracteres)

Operaciones que acepta (campo "op" en el JSON):
  - login          : autentica con email/password → devuelve JWT + rol
  - verify         : verifica un JWT vigente → devuelve user_id + rol
  - create_user    : crea un usuario nuevo (solo técnicos)
  - update_user    : activa/desactiva un usuario (solo técnicos)
  - list_users     : lista todos los usuarios (solo técnicos)
  - update_rol     : cambia el rol de un usuario (solo técnicos)

Formato de mensajes entrantes:
  login       → {"op": "login",       "email": "x@x.com", "password": "clave"}
  verify      → {"op": "verify",      "token": "eyJ..."}
  create_user → {"op": "create_user", "token": "eyJ...(técnico)",
                  "email": "nuevo@scg.cl", "password": "clave",
                  "nombre": "Juan Pérez", "rol": "operario|contador|tecnico"}
  update_user → {"op": "update_user", "token": "eyJ...(técnico)",
                  "user_id": "uuid", "activo": true|false}
  list_users  → {"op": "list_users",  "token": "eyJ...(técnico)"}
  update_rol  → {"op": "update_rol",  "token": "eyJ...(técnico)",
                  "user_id": "uuid", "rol": "operario|contador|tecnico"}

Formato de respuesta:
  éxito  → {"status": "ok", ...campos según operación}
  error  → {"status": "error", "mensaje": "Descripción"}
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from soa_lib import connect_to_bus, send_message, receive_message

load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────────
SERVICE_NAME = "sauth"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")

ROLES_VALIDOS = {"operario", "contador", "tecnico"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def test_supabase():
    try:
        sb = get_supabase()
        sb.table("profiles").select("id").limit(1).execute()
        print("[sauth] ✅ Conexión exitosa a Supabase")
    except Exception as e:
        print(f"[sauth] ❌ Error conectando a Supabase: {e}")
        raise


def get_supabase() -> Client:
    """Crea y devuelve el cliente de Supabase con clave service_role."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _obtener_perfil_por_token(sb: Client, token: str) -> dict:
    """
    Dado un JWT, devuelve el perfil completo del usuario.
    Lanza excepción si el token es inválido o el usuario está inactivo.
    """
    resp    = sb.auth.get_user(token)
    user_id = resp.user.id

    perfil = (
        sb.table("profiles")
          .select("id, nombre, email, rol, activo")
          .eq("id", user_id)
          .single()
          .execute()
    )
    datos = perfil.data

    # FIX: un usuario desactivado no puede operar aunque tenga token vigente
    if not datos.get("activo", False):
        raise PermissionError("Usuario desactivado")

    return datos


def _verificar_tecnico(sb: Client, token: str) -> dict:
    """
    Verifica que el token pertenece a un técnico activo.
    Devuelve el perfil si es técnico, lanza excepción si no.
    """
    perfil = _obtener_perfil_por_token(sb, token)
    if perfil.get("rol") != "tecnico":
        raise PermissionError("Solo un técnico puede realizar esta acción")
    return perfil


# ── Operaciones ────────────────────────────────────────────────────────────────

def op_login(payload: dict) -> dict:
    email    = payload.get("email", "").strip()
    password = payload.get("password", "")

    if not email or not password:
        return {"status": "error", "mensaje": "email y password son obligatorios"}

    try:
        sb   = get_supabase()
        resp = sb.auth.sign_in_with_password({"email": email, "password": password})

        token   = resp.session.access_token
        user_id = resp.user.id

        perfil = (
            sb.table("profiles")
              .select("nombre, rol, activo")
              .eq("id", user_id)
              .single()
              .execute()
        )
        data = perfil.data

        if not data.get("activo", False):
            sb.auth.sign_out()
            return {"status": "error", "mensaje": "Usuario deshabilitado. Contacte al técnico."}

        return {
            "status":  "ok",
            "token":   token,
            "user_id": user_id,
            "email":   email,
            "nombre":  data.get("nombre"),
            "rol":     data.get("rol"),
        }

    except Exception:
        # FIX: no exponer detalle interno de la excepción
        return {"status": "error", "mensaje": "Credenciales inválidas"}


def op_verify(payload: dict) -> dict:
    token = payload.get("token", "")
    reply_to = payload.get("reply_to")

    # ─────────────────────────────
    # 🔧 MODO TEST (PING DE TOKEN FALSO)
    # ─────────────────────────────
    if token == "test-token":
        return {
            "status": "ok",
            "user_id": "test-user",
            "nombre": "Usuario de prueba",
            "email": "test@local",
            "rol": "tecnico",
            "reply_to": reply_to
        }

    if not token:
        return {
            "status": "error",
            "mensaje": "token es obligatorio",
            "reply_to": reply_to
        }

    try:
        sb = get_supabase()
        perfil = _obtener_perfil_por_token(sb, token)

        return {
            "status": "ok",
            "user_id": perfil["id"],
            "nombre": perfil["nombre"],
            "email": perfil["email"],
            "rol": perfil["rol"],
            "reply_to": reply_to
        }

    except PermissionError as e:
        return {"status": "error", "mensaje": str(e), "reply_to": reply_to}
    except Exception:
        return {"status": "error", "mensaje": "Token inválido", "reply_to": reply_to}

def op_create_user(payload: dict) -> dict:
    token     = payload.get("token", "")
    email     = payload.get("email", "").strip()
    password  = payload.get("password", "")
    nombre    = payload.get("nombre", "").strip()
    rol_nuevo = payload.get("rol", "").strip()

    if not all([token, email, password, nombre, rol_nuevo]):
        return {"status": "error",
                "mensaje": "token, email, password, nombre y rol son obligatorios"}

    if rol_nuevo not in ROLES_VALIDOS:
        return {"status": "error",
                "mensaje": f"rol inválido. Valores posibles: {sorted(ROLES_VALIDOS)}"}

    try:
        sb = get_supabase()
        _verificar_tecnico(sb, token)

        resp_auth = sb.auth.admin.create_user({
            "email":         email,
            "password":      password,
            "email_confirm": True,
        })
        nuevo_user_id = resp_auth.user.id

        sb.table("profiles").update({
            "nombre": nombre,
            "rol": rol_nuevo
        }).eq("id", nuevo_user_id).execute()

        return {
            "status":  "ok",
            "user_id": nuevo_user_id,
            "email":   email,
            "nombre":  nombre,
            "rol":     rol_nuevo,
        }

    except PermissionError as e:
        return {"status": "error", "mensaje": str(e)}
    except Exception as e:
        return {"status": "error", "mensaje": f"Error al crear usuario: {str(e)}"}


def op_update_user(payload: dict) -> dict:
    token   = payload.get("token", "")
    user_id = payload.get("user_id", "")
    activo  = payload.get("activo")

    if not token or not user_id or activo is None:
        return {"status": "error",
                "mensaje": "token, user_id y activo son obligatorios"}

    if not isinstance(activo, bool):
        return {"status": "error", "mensaje": "activo debe ser true o false"}

    try:
        sb     = get_supabase()
        perfil = _verificar_tecnico(sb, token)

        # FIX: el técnico no puede desactivarse a sí mismo
        if perfil["id"] == user_id and not activo:
            return {"status": "error", "mensaje": "No puedes desactivarte a ti mismo"}

        resultado = (
            sb.table("profiles")
              .update({"activo": activo})
              .eq("id", user_id)
              .execute()
        )

        if not resultado.data:
            return {"status": "error",
                    "mensaje": f"No se encontró el usuario con id '{user_id}'"}

        return {"status": "ok", "user_id": user_id, "activo": activo}

    except PermissionError as e:
        return {"status": "error", "mensaje": str(e)}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def op_list_users(payload: dict) -> dict:
    """Lista todos los usuarios. Solo técnicos."""
    token = payload.get("token", "")
    if not token:
        return {"status": "error", "mensaje": "token es obligatorio"}

    try:
        sb = get_supabase()
        _verificar_tecnico(sb, token)

        resp = (
            sb.table("profiles")
              .select("id, nombre, email, rol, activo, created_at")
              .order("created_at", desc=False)
              .execute()
        )
        return {"status": "ok", "usuarios": resp.data}

    except PermissionError as e:
        return {"status": "error", "mensaje": str(e)}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def op_update_rol(payload: dict) -> dict:
    """Cambia el rol de un usuario. Solo técnicos."""
    token     = payload.get("token", "")
    user_id   = payload.get("user_id", "")
    nuevo_rol = payload.get("rol", "").strip()

    if not token or not user_id or not nuevo_rol:
        return {"status": "error",
                "mensaje": "token, user_id y rol son obligatorios"}

    if nuevo_rol not in ROLES_VALIDOS:
        return {"status": "error",
                "mensaje": f"rol inválido. Valores posibles: {sorted(ROLES_VALIDOS)}"}

    try:
        sb = get_supabase()
        _verificar_tecnico(sb, token)

        resultado = (
            sb.table("profiles")
              .update({"rol": nuevo_rol})
              .eq("id", user_id)
              .execute()
        )

        if not resultado.data:
            return {"status": "error",
                    "mensaje": f"No se encontró el usuario con id '{user_id}'"}

        return {"status": "ok", "user_id": user_id, "rol": nuevo_rol}

    except PermissionError as e:
        return {"status": "error", "mensaje": str(e)}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def op_ping(payload: dict) -> dict:
    return {
        "status": "ok",
        "mensaje": "pong",
        "reply_to": payload.get("reply_to")
    }
# ── Dispatcher ─────────────────────────────────────────────────────────────────

OPERACIONES = {
    "login":       op_login,
    "verify":      op_verify,
    "create_user": op_create_user,
    "update_user": op_update_user,
    "list_users":  op_list_users,
    "update_rol":  op_update_rol,
    "ping": op_ping   # 👈 NUEVO
}


def procesar_mensaje(raw_payload: str) -> dict:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {"status": "error", "mensaje": "El payload no es JSON válido"}

    op = payload.get("op")
    if op not in OPERACIONES:
        return {"status": "error",
                "mensaje": f"Operación '{op}' desconocida. Válidas: {sorted(OPERACIONES)}"}

    return OPERACIONES[op](payload)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    test_supabase()
    sock = connect_to_bus()

    try:
        print(f"[sauth] Registrando servicio '{SERVICE_NAME}' en el bus...")
        send_message(sock, "sinit", SERVICE_NAME)

        confirmacion = receive_message(sock)
        print(f"[sauth] Bus confirmó: {confirmacion!r}")
        print("[sauth] Listo para recibir mensajes.\n")

        while True:
            data = receive_message(sock)
            print(data) 
            if not data:
                print("[sauth] Bus cerró la conexión.")
                break

            raw_payload = data[5:].decode("utf-8")
            print(f"[sauth] ← {raw_payload}")

            payload = json.loads(raw_payload)
            destino = payload.get("reply_to", SERVICE_NAME)

            respuesta = procesar_mensaje(raw_payload)
            respuesta_str = json.dumps(respuesta, ensure_ascii=False)

            send_message(sock, destino, respuesta_str)
            print(f"[sauth] → {respuesta_str}\n")

    except KeyboardInterrupt:
        print("\n[sauth] Detenido por el usuario.")
    except Exception as e:
        print(f"[sauth] Error inesperado: {e}")
    finally:
        sock.close()
        print("[sauth] Socket cerrado.")


if __name__ == "__main__":
    main()