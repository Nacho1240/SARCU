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
    Abre una conexión TCP al bus, envía el payload al servicio indicado
    y devuelve la respuesta parseada como dict.

    Cada llamada abre y cierra su propio socket (simple y correcto
    para el volumen de una aplicación universitaria).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((BUS_HOST, BUS_PORT))

        # Formato: [5-bytes-largo][5-bytes-servicio][payload]
        payload_bytes = json.dumps(payload).encode("utf-8")
        content       = service_name.encode() + payload_bytes
        message       = str(len(content)).zfill(5).encode() + content
        sock.sendall(message)

        # Leer respuesta
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
    result = call_service("sgast", {
        "op":       "cambiar_estado",
        "token":    body.get("token"),
        "gasto_id": gasto_id,
        "estado":   body.get("estado"),          # aprobado | rechazado | pendiente
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

@app.get("/reportes/consolidado")
def reporte_consolidado(token: str, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None):
    result = call_service("srept", {
        "op":          "consolidado",
        "token":       token,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result
