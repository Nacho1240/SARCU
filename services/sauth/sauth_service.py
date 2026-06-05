"""
Servicio de Autenticación — SCG (Sistema de Control de Gastos)
Nombre en el bus: "sauth"  (exactamente 5 caracteres)

Operaciones que acepta (campo "op" en el JSON):
  - login        : autentica con email/password → devuelve JWT + rol
  - verify       : verifica un JWT vigente → devuelve user_id + rol
  - create_user  : crea un usuario nuevo (solo técnicos) → devuelve user_id
  - update_user  : activa/desactiva un usuario (solo técnicos)

Formato de mensajes entrantes:
  login       → {"op": "login",       "email": "x@x.com", "password": "clave"}
  verify      → {"op": "verify",      "token": "eyJ..."}
  create_user → {"op": "create_user", "token": "eyJ...(técnico)",
                  "email": "nuevo@scg.cl", "password": "clave",
                  "nombre": "Juan Pérez", "rol": "operario|contador|tecnico"}
  update_user → {"op": "update_user", "token": "eyJ...(técnico)",
                  "user_id": "uuid", "activo": true|false}

Formato de respuesta:
  éxito  → {"status": "ok", ...campos según operación}
  error  → {"status": "error", "mensaje": "Descripción"}
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from soa_lib import connect_to_bus, send_message, receive_message

# Cargar variables de entorno
load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────────
SERVICE_NAME = "sauth"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")


# ── Helpers ────────────────────────────────────────────────────────────────────
def test_supabase():
    try:
        sb = get_supabase()

        # Consulta simple
        sb.table("profiles").select("id").limit(1).execute()

        print("[sauth] ✅ Conexión exitosa a Supabase")

    except Exception as e:
        print(f"[sauth] ❌ Error conectando a Supabase: {e}")
        raise
def get_supabase() -> Client:
    """Crea y devuelve el cliente de Supabase con clave service_role."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _obtener_rol_por_token(sb: Client, token: str) -> tuple[str | None, str | None]:
    """
    Dado un JWT, devuelve (user_id, rol).
    Si el token es inválido lanza excepción (el llamador la captura).
    """
    resp    = sb.auth.get_user(token)
    user_id = resp.user.id
    perfil  = (
        sb.table("profiles")
          .select("rol")
          .eq("id", user_id)
          .single()
          .execute()
    )
    rol = perfil.data.get("rol", "desconocido")
    return user_id, rol


# ── Operaciones ────────────────────────────────────────────────────────────────

def op_login(payload: dict) -> dict:
    """
    Autentica al usuario con Supabase Auth.
    Solo permite el ingreso si el perfil está activo.
    """
    email    = payload.get("email", "").strip()
    password = payload.get("password", "")

    if not email or not password:
        return {"status": "error", "mensaje": "email y password son obligatorios"}

    try:
        sb = get_supabase()

        # 1. Autenticar contra Supabase Auth
        resp    = sb.auth.sign_in_with_password({"email": email, "password": password})
        token   = resp.session.access_token
        user_id = resp.user.id

        # 2. Obtener perfil: rol y estado activo
        perfil = (
            sb.table("profiles")
              .select("rol, activo")
              .eq("id", user_id)
              .single()
              .execute()
        )
        data = perfil.data

        # 3. Verificar que el usuario esté habilitado
        if not data.get("activo", False):
            # Cerramos la sesión recién creada para no dejar tokens huérfanos
            sb.auth.sign_out()
            return {"status": "error", "mensaje": "Usuario deshabilitado. Contacte al técnico."}

        return {
            "status":  "ok",
            "token":   token,
            "user_id": user_id,
            "email":   email,
            "rol":     data.get("rol", "desconocido"),
        }

    except Exception as e:
        return {"status": "error", "mensaje": f"Credenciales inválidas: {str(e)}"}


def op_verify(payload: dict) -> dict:
    """
    Verifica que un JWT siga siendo válido.
    Devuelve user_id y rol. Útil para que otros servicios validen tokens
    sin necesidad de contactar Supabase directamente.
    """
    token = payload.get("token", "")

    if not token:
        return {"status": "error", "mensaje": "token es obligatorio"}

    try:
        sb = get_supabase()
        user_id, rol = _obtener_rol_por_token(sb, token)

        return {
            "status":  "ok",
            "user_id": user_id,
            "rol":     rol,
        }

    except Exception as e:
        return {"status": "error", "mensaje": f"Token inválido o expirado: {str(e)}"}


def op_create_user(payload: dict) -> dict:
    """
    Crea un usuario nuevo en Supabase Auth + inserta su perfil.
    Solo los técnicos pueden hacer esto (el firmante del token debe tener rol 'tecnico').

    Campos requeridos en el payload:
      token    : JWT del técnico que hace la petición
      email    : email del nuevo usuario
      password : contraseña del nuevo usuario
      nombre   : nombre completo
      rol      : "operario" | "contador" | "tecnico"
    """
    token    = payload.get("token", "")
    email    = payload.get("email", "").strip()
    password = payload.get("password", "")
    nombre   = payload.get("nombre", "").strip()
    rol_nuevo = payload.get("rol", "").strip()

    # Validaciones básicas
    if not all([token, email, password, nombre, rol_nuevo]):
        return {"status": "error",
                "mensaje": "token, email, password, nombre y rol son obligatorios"}

    roles_validos = {"operario", "contador", "tecnico"}
    if rol_nuevo not in roles_validos:
        return {"status": "error",
                "mensaje": f"rol inválido. Valores posibles: {sorted(roles_validos)}"}

    try:
        sb = get_supabase()

        # 1. Verificar que el solicitante sea técnico
        _, rol_solicitante = _obtener_rol_por_token(sb, token)
        if rol_solicitante != "tecnico":
            return {"status": "error",
                    "mensaje": "Solo un técnico puede crear usuarios"}

        # 2. Crear el usuario en Supabase Auth (con service_role)
        #    email_confirm=True lo crea ya verificado, sin necesitar correo
        resp_auth = sb.auth.admin.create_user({
            "email":            email,
            "password":         password,
            "email_confirm":    True,
        })
        nuevo_user_id = resp_auth.user.id

        # 3. Insertar el perfil en la tabla profiles
        sb.table("profiles").insert({
            "id":     nuevo_user_id,
            "nombre": nombre,
            "email":  email,
            "rol":    rol_nuevo,
            "activo": True,
        }).execute()

        return {
            "status":  "ok",
            "user_id": nuevo_user_id,
            "email":   email,
            "rol":     rol_nuevo,
        }

    except Exception as e:
        return {"status": "error", "mensaje": f"Error al crear usuario: {str(e)}"}


def op_update_user(payload: dict) -> dict:
    """
    Activa o desactiva un usuario (campo 'activo' en profiles).
    Solo los técnicos pueden hacer esto.

    Campos requeridos:
      token   : JWT del técnico
      user_id : UUID del usuario a modificar
      activo  : true | false
    """
    token   = payload.get("token", "")
    user_id = payload.get("user_id", "")
    activo  = payload.get("activo")

    if not token or not user_id or activo is None:
        return {"status": "error",
                "mensaje": "token, user_id y activo son obligatorios"}

    if not isinstance(activo, bool):
        return {"status": "error", "mensaje": "activo debe ser true o false"}

    try:
        sb = get_supabase()

        # 1. Verificar que el solicitante sea técnico
        _, rol_solicitante = _obtener_rol_por_token(sb, token)
        if rol_solicitante != "tecnico":
            return {"status": "error",
                    "mensaje": "Solo un técnico puede modificar usuarios"}

        # 2. Actualizar el campo activo en profiles
        resultado = (
            sb.table("profiles")
              .update({"activo": activo})
              .eq("id", user_id)
              .execute()
        )

        if not resultado.data:
            return {"status": "error",
                    "mensaje": f"No se encontró el usuario con id '{user_id}'"}

        return {
            "status":  "ok",
            "user_id": user_id,
            "activo":  activo,
        }

    except Exception as e:
        return {"status": "error", "mensaje": f"Error al actualizar usuario: {str(e)}"}


# ── Dispatcher ─────────────────────────────────────────────────────────────────

OPERACIONES = {
    "login":       op_login,
    "verify":      op_verify,
    "create_user": op_create_user,
    "update_user": op_update_user,
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
        ops_validas = sorted(OPERACIONES.keys())
        return {"status": "error",
                "mensaje": f"Operación '{op}' desconocida. Válidas: {ops_validas}"}

    return OPERACIONES[op](payload)


# ── Main: conexión al bus y bucle principal ────────────────────────────────────

def main():
    test_supabase()
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

            # Los primeros 5 bytes son el nombre del servicio remitente (lo ignoramos)
            raw_payload = data[5:].decode("utf-8")
            print(f"[sauth] Mensaje recibido: {raw_payload}")

            respuesta     = procesar_mensaje(raw_payload)
            respuesta_str = json.dumps(respuesta, ensure_ascii=False)

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
