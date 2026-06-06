"""
Servicio de Saldos — SCG
Nombre en el bus: "ssald" (exactamente 5 caracteres)

Operaciones:
- mi_saldo: obtener saldo disponible del usuario actual (cualquier rol)
- saldo_operario: obtener saldo de un operario específico (solo CONTADOR)
- cambiar_estado: aprobar/rechazar gasto y actualizar saldo (solo CONTADOR)

Roles:
- operador/obrera: solo ve su propio saldo
- técnico: solo ve su propio saldo (maneja usuarios pero no saldos)
- contador: puede ver saldos de todos los operarios Y aprobar/rechazar gastos
"""

import json
import os
import sys
from datetime import datetime, timezone
from supabase import create_client

# Importar desde bus/ del profesor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bus'))
from soa_lib import connect_to_bus, send_message, receive_message

SERVICE_NAME = "ssald"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase = None

def init_supabase():
    """Inicializa la conexión a Supabase (una sola vez)."""
    global supabase
    if not supabase:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

def verificar_token(token: str) -> dict | None:
    """ 
    Verifica si el token es válido consultando Supabase auth. 
    Devuelve dict con user_id y rol si es válido, None si no. 
    """
    try:
        db = init_supabase()
        # Obtener usuario del token
        data = db.auth.get_user(token)
        if data.user:
            # CORREGIDO: Se cambia "perfiles" por "profiles"
            perfil = db.table("profiles").select("rol").eq("id", data.user.id).single().execute()
            if perfil.data:
                return {
                    "user_id": data.user.id,
                    "email": data.user.email,
                    "rol": perfil.data.get("rol", "operador")
                }
    except Exception as e:
        print(f"[ssald] Error verificando token: {e}")
    return None

def obtener_mi_saldo(user_id: str) -> dict:
    """ 
    Obtiene el saldo disponible del usuario actual. 
    CUALQUIER ROL puede usar esta operación. 
    """
    try:
        db = init_supabase()
        # CORREGIDO: Se cambia "perfiles" por "profiles"
        perfil = db.table("profiles").select("saldo_disponible").eq("id", user_id).single().execute()
        if perfil.data:
            return {
                "status": "ok",
                "saldo_disponible": perfil.data.get("saldo_disponible", 0)
            }
        else:
            return {"status": "error", "mensaje": "Perfil no encontrado"}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def obtener_saldo_operario(user_id_solicitante: str, rol_solicitante: str, user_id_operario: str) -> dict:
    """ 
    Obtiene el saldo de un operario específico. 
    SOLO el CONTADOR puede usar esta operación. 
    """
    try:
        # Verificar que el solicitante sea CONTADOR
        if rol_solicitante != "contador":
            return {
                "status": "error",
                "mensaje": f"Solo CONTADOR puede ver saldos de otros operarios. Tu rol es: {rol_solicitante}"
            }
        
        # Obtener saldo del operario
        db = init_supabase()
        # CORREGIDO: Se cambia "perfiles" por "profiles"
        perfil = db.table("profiles").select("saldo_disponible, nombre, apellido, rol").eq("id", user_id_operario).single().execute()
        if perfil.data:
            return {
                "status": "ok",
                "saldo_disponible": perfil.data.get("saldo_disponible", 0),
                "nombre": perfil.data.get("nombre", ""),
                "apellido": perfil.data.get("apellido", ""),
                "rol": perfil.data.get("rol", "")
            }
        else:
            return {"status": "error", "mensaje": "Operario no encontrado"}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def cambiar_estado(user_id_contador: str, rol_contador: str, gasto_id: str, nuevo_estado: str, motivo: str = "") -> dict:
    """ 
    Aprueba o rechaza un gasto y actualiza el saldo del operario si es aprobado. 
    SOLO el CONTADOR puede usar esta operación. 
    """
    try:
        # Verificar que sea CONTADOR
        if rol_contador != "contador":
            return {
                "status": "error",
                "mensaje": f"Solo CONTADOR puede cambiar estado de gastos. Tu rol es: {rol_contador}"
            }
            
        db = init_supabase()
        
        # Validar estado
        nuevo_estado = nuevo_estado.lower().strip()
        if nuevo_estado not in ["aprobado", "rechazado"]:
            return {
                "status": "error", 
                "mensaje": f"Estado inválido: {nuevo_estado}. Solo se puede cambiar a: aprobado o rechazado"
            }
            
        if nuevo_estado == "rechazado" and not motivo.strip():
            return {"status": "error", "mensaje": "El motivo de rechazo es obligatorio"}
            
        # Obtener el gasto
        gasto_res = db.table("gastos").select("*").eq("id", gasto_id).single().execute()
        if not gasto_res.data:
            return {"status": "error", "mensaje": "Gasto no encontrado"}
            
        gasto = gasto_res.data
        
        if gasto["estado"] != "pendiente":
            return {
                "status": "error", 
                "mensaje": f"El gasto ya está {gasto['estado']} (definitivo). No se puede cambiar"
            }
            
        # Preparar update del gasto
        update_gasto = {
            "estado": nuevo_estado,
            "contador_id": user_id_contador,
            "fecha_revision": datetime.now(timezone.utc).isoformat(),
        }
        
        if nuevo_estado == "rechazado":
            update_gasto["motivo_rechazo"] = motivo.strip()
        else:
            update_gasto["motivo_rechazo"] = None
            
        # Actualizar gasto
        gasto_actualizado = db.table("gastos").update(update_gasto).eq("id", gasto_id).execute()
        if not gasto_actualizado.data:
            return {"status": "error", "mensaje": "Error al actualizar gasto"}
            
        # SI ES APROBADO: deducir del saldo del operario
        if nuevo_estado == "approved" or nuevo_estado == "aprobado": # Flexibilidad por si cambia el string de estado
            operario_id = gasto["operario_id"]
            monto = gasto["monto"]
            
            # Obtener saldo actual del operario desde "profiles"
            # CORREGIDO: Se cambia "perfiles" por "profiles"
            perfil_res = db.table("profiles").select("saldo_disponible").eq("id", operario_id).single().execute()
            if not perfil_res.data:
                return {"status": "error", "mensaje": "Perfil del operario no encontrado"}
                
            saldo_actual = perfil_res.data.get("saldo_disponible", 0)
            nuevo_saldo = saldo_actual - monto
            
            # Actualizar saldo en "profiles"
            # CORREGIDO: Se cambia "perfiles" por "profiles"
            db.table("profiles").update({"saldo_disponible": nuevo_saldo}).eq("id", operario_id).execute()
            
            return {
                "status": "ok",
                "gasto": gasto_actualizado.data[0],
                "mensaje": f"Gasto APROBADO. Saldo deducido: ${monto:,.0f}",
                "saldo_anterior": saldo_actual,
                "saldo_nuevo": nuevo_saldo
            }
            
        return {
            "status": "ok",
            "gasto": gasto_actualizado.data[0],
            "mensaje": f"Gasto RECHAZADO. Motivo: {motivo.strip()}"
        }
        
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def procesar_mensaje(raw_payload: str) -> dict:
    """ Procesa un mensaje JSON del bus y ejecuta la operación solicitada. """
    try:
        payload = json.loads(raw_payload)
        op = payload.get("op")
        token = payload.get("token")
        
        usuario_verificado = verificar_token(token)
        if not usuario_verificado:
            return {"status": "error", "mensaje": "Token inválido o expirado"}
            
        if op == "mi_saldo":
            return obtener_mi_saldo(usuario_verificado["user_id"])
            
        elif op == "saldo_operario":
            user_id_operario = payload.get("user_id")
            if not user_id_operario:
                return {"status": "error", "mensaje": "user_id requerido"}
            return obtener_saldo_operario(
                usuario_verificado["user_id"], 
                usuario_verificado["rol"], 
                user_id_operario
            )
            
        elif op == "cambiar_estado":
            gasto_id = payload.get("gasto_id")
            nuevo_estado = payload.get("estado")
            motivo = payload.get("motivo", "")
            
            if not gasto_id:
                return {"status": "error", "mensaje": "gasto_id requerido"}
            if not nuevo_estado:
                return {"status": "error", "mensaje": "estado requerido"}
                
            return cambiar_estado(
                usuario_verificado["user_id"], 
                usuario_verificado["rol"], 
                gasto_id, 
                nuevo_estado, 
                motivo
            )
            
        else:
            return {"status": "error", "mensaje": f"Operación '{op}' no implementada"}
            
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def main():
    sock = connect_to_bus()
    try:
        print(f"[ssald] Registrando servicio '{SERVICE_NAME}'...")
        send_message(sock, "sinit", SERVICE_NAME)
        confirmacion = receive_message(sock)
        
        print(f"[ssald] Bus confirmó: {confirmacion!r}")
        print(f"[ssald] Listo.\n")
        
        while True:
            data = receive_message(sock)
            if not data:
                print(f"[ssald] Bus cerró la conexión.")
                break
                
            raw_payload = data[5:].decode("utf-8")
            print(f"[ssald] Mensaje recibido: {raw_payload}")
            
            respuesta = procesar_mensaje(raw_payload)
            
            send_message(sock, SERVICE_NAME, json.dumps(respuesta))
            print(f"[ssald] Respuesta enviada: {respuesta}\n")
            
    except KeyboardInterrupt:
        print(f"\n[ssald] Detenido.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()