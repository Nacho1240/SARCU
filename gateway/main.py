"""
Gateway API — SCG
Puente entre el frontend React (HTTP/REST) y el Bus SOA (TCP).

El frontend no puede hablar TCP directamente, así que cada request HTTP
se traduce a un mensaje TCP al bus y la respuesta vuelve como JSON.
"""
import json
import os
import socket
import random
import string

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

BUS_HOST = os.getenv("BUS_HOST", "localhost")
BUS_PORT = int(os.getenv("BUS_PORT", "5000"))

app = FastAPI(title="SCG Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En producción: restringir al dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Función central: TCP call al bus ──────────────────────────────────────────

def call_service(service_name: str, payload: dict) -> dict:
    """
    Abre una conexión TCP al bus, se registra como un cliente aleatorio,
    envía el payload al servicio indicado y devuelve la respuesta.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((BUS_HOST, BUS_PORT))

        # ── Paso 1: Registrarse en el bus con sinit (Nombre Aleatorio) ────────
        # Generamos 5 letras al azar para evitar que peticiones concurrentes choquen
        my_name   = "".join(random.choices(string.ascii_lowercase, k=5))
        reg_name  = my_name.encode()               
        reg_content = b"sinit" + reg_name
        reg_msg   = str(len(reg_content)).zfill(5).encode() + reg_content
        sock.sendall(reg_msg)

        # Esperar ACK del bus (responde "sinit" + "OK")
        ack_len_raw = sock.recv(5)
        if not ack_len_raw:
            raise RuntimeError("Bus no respondió al registro sinit.")
        ack_amount = int(ack_len_raw)
        ack_data = b""
        while len(ack_data) < ack_amount:
            chunk = sock.recv(ack_amount - len(ack_data))
            if not chunk:
                break
            ack_data += chunk

        # ── Paso 2: Enviar el mensaje al servicio destino ─────────────────────
        payload["reply_to"] = my_name          
        payload_bytes = json.dumps(payload).encode("utf-8")
        content       = service_name.encode() + payload_bytes
        message       = str(len(content)).zfill(5).encode() + content
        sock.sendall(message)

        # ── Paso 3: Leer la respuesta que el servicio envió de vuelta ─────────
        raw_len = sock.recv(5)
        if not raw_len:
            raise RuntimeError("Bus cerró la conexión sin responder.")
        amount = int(raw_len)
        data = b""
        while len(data) < amount:
            chunk = sock.recv(amount - len(data))
            if not chunk:
                break
            data += chunk

        return json.loads(data[5:].decode("utf-8"))

    except ConnectionRefusedError:
        raise HTTPException(status_code=503, detail="Bus SOA no disponible.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sock.close()


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "bus": f"{BUS_HOST}:{BUS_PORT}"}


# ── Auth (/auth) ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    str
    password: str

@app.post("/auth/login")
def login(req: LoginRequest):
    result = call_service("sauth", {
        "op":       "login",
        "email":    req.email,
        "password": req.password,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=401, detail=result.get("mensaje"))
    return result


@app.get("/auth/verify")
def verify(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado.")
    token = authorization.split(" ", 1)[1]
    result = call_service("sauth", {"op": "verify", "token": token})
    if result.get("status") == "error":
        raise HTTPException(status_code=401, detail=result.get("mensaje"))
    return result

class RegistroRequest(BaseModel):
    token: str
    email: str
    password: str
    nombre: str
    rol: str
    
@app.post("/auth/registro")
def registro(req: RegistroRequest):
    result = call_service("sauth", {
        "op":       "create_user",
        "token":    req.token,
        "email":    req.email,
        "password": req.password,
        "nombre":   req.nombre,
        "rol":      req.rol
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result

@app.get("/auth/usuarios")
def listar_usuarios(token: str):
    result = call_service("sauth", {
        "op": "list_users",
        "token": token
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


# ── Gestión de Usuarios (Técnico) ─────────────────────────────────────────────

class ModificarUsuarioRequest(BaseModel):
    token: str
    rol: str
    saldo_disponible: float

@app.patch("/usuarios/{user_id}")
def modificar_usuario(user_id: str, req: ModificarUsuarioRequest):
    # 1. Mandamos a actualizar el rol al servicio de Autenticación/Usuarios
    res_rol = call_service("sauth", {
        "op": "update_rol",  # <--- CORRIGE ESTO AQUÍ
        "token": req.token,
        "user_id": user_id,
        "rol": req.rol
    })
    if res_rol.get("status") == "error":
        raise HTTPException(status_code=400, detail=res_rol.get("mensaje"))

    # 2. Mandamos a asignar el saldo inicial al servicio de Saldos
    res_saldo = call_service("ssald", {
        "op": "asignar_saldo", 
        "token": req.token,
        "user_id": user_id,
        "saldo": req.saldo_disponible
    })
    if res_saldo.get("status") == "error":
        raise HTTPException(status_code=400, detail=res_saldo.get("mensaje"))

    return {"status": "ok", "mensaje": "Usuario y saldo actualizados correctamente"}


@app.delete("/usuarios/{user_id}")
def eliminar_usuario(user_id: str, token: str):
    # Mandamos la orden de eliminación lógica o física al servicio de usuarios
    result = call_service("sauth", {
        "op": "delete_user",
        "token": token,
        "user_id": user_id
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


# ── Gastos (/gastos) ──────────────────────────────────────────────────────────

class GastoRequest(BaseModel):
    token:    str
    monto:    float
    concepto: str
    fecha:    str                     # ISO: "2026-06-03"
    comprobanteUrl: Optional[str] = None

@app.post("/gastos")
def crear_gasto(req: GastoRequest):
    result = call_service("sgast", {
        "op":             "crear",
        "token":          req.token,
        "monto":          req.monto,
        "concepto":       req.concepto,
        "fecha":          req.fecha,
        "comprobanteUrl": req.comprobanteUrl,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


@app.get("/gastos")
def listar_gastos(token: str, estado: Optional[str] = None):
    result = call_service("sgast", {
        "op":     "listar",
        "token":  token,
        "estado": estado,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


@app.patch("/gastos/{gasto_id}/estado")
def cambiar_estado(gasto_id: str, body: dict):
    result = call_service("ssald", {   # <--- CAMBIAR 'sgast' POR 'ssald'
        "op":       "cambiar_estado",
        "token":    body.get("token"),
        "gasto_id": gasto_id,
        "estado":   body.get("estado"),          
        "motivo":   body.get("motivo", "")  # <--- AGREGAR EL MOTIVO
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result

# ── Saldos (/saldos) ──────────────────────────────────────────────────────────

@app.get("/saldos/mio")
def mi_saldo(token: str):
    result = call_service("ssald", {"op": "mi_saldo", "token": token})
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


@app.get("/saldos/{user_id}")
def saldo_operario(user_id: str, token: str):
    result = call_service("ssald", {
        "op":      "saldo_operario",
        "token":   token,
        "user_id": user_id,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=403, detail=result.get("mensaje"))
    return result


# ── Comprobantes (/comprobantes) ──────────────────────────────────────────────

@app.get("/comprobantes/{gasto_id}")
def url_comprobante(gasto_id: str, token: str):
    result = call_service("scomp", {
        "op":       "obtener_url",
        "token":    token,
        "gasto_id": gasto_id,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


# ── Reportes (/reportes) ──────────────────────────────────────────────────────

@app.get("/reportes/resumen")
def reporte_resumen(token: str):
    result = call_service("srept", {"op": "resumen", "token": token})
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result

@app.get("/reportes/listar")
def reporte_listar(
    token: str, 
    estado: str = "all", 
    fecha_filtro: str = "all", 
    monto_filtro: str = "all", 
    search: str = ""
):
    result = call_service("srept", {
        "op": "listar_gastos",
        "token": token,
        "estado": estado,
        "fecha_filtro": fecha_filtro,
        "monto_filtro": monto_filtro,
        "search": search
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result

@app.post("/reportes/pdf")
def reporte_pdf(body: dict):
    result = call_service("srept", {
        "op": "reporte_pdf",
        "token": body.get("token"),
        "gasto_ids": body.get("gasto_ids", [])
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result