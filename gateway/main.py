"""
Gateway API — SCG
Puente entre el frontend React (HTTP/REST) y el Bus SOA (TCP).

El frontend no puede hablar TCP directamente, así que cada request HTTP
se traduce a un mensaje TCP al bus y la respuesta vuelve como JSON.
"""
import json
import os
import socket

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
    Abre una conexión TCP al bus, se registra como 'gateway' (sinit),
    envía el payload al servicio indicado y devuelve la respuesta.

    El bus requiere que todo cliente se registre con 'sinit' antes de
    poder enviar o recibir mensajes enrutados.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((BUS_HOST, BUS_PORT))

        # ── Paso 1: Registrarse en el bus con sinit ───────────────────────────
        # El bus ignora cualquier mensaje de clientes no registrados.
        my_name   = "gatew"                        # exactamente 5 bytes
        reg_name  = my_name.encode()               # b"gatew"
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
        # ack_data = b"sinitOK" — ignoramos el contenido, solo verificamos llegada

        # ── Paso 2: Enviar el mensaje al servicio destino ─────────────────────
        # Formato: [5-bytes-longitud][5-bytes-destino][payload-JSON]
        # reply_to indica al servicio a qué nombre del bus debe responder.
        # Sin este campo, los servicios responden a sí mismos y la respuesta
        # nunca llega al gateway (se queda colgado infinitamente).
        payload["reply_to"] = my_name          # "gatew"
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

        # data = [5-bytes-origen][payload-JSON]
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
    # Llama a la operación 'resumen' que ya validamos
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
    # Llama a la operación 'listar_gastos'
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
    # Llama a 'reporte_pdf' (espera gasto_ids como lista en el body)
    result = call_service("srept", {
        "op": "reporte_pdf",
        "token": body.get("token"),
        "gasto_ids": body.get("gasto_ids", [])
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result