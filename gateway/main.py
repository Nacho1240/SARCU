"""
Gateway API — SCG (Conexión persistente al bus SOA)
"""
import json
import os
import socket
import threading
import queue
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BUS_HOST = os.getenv("BUS_HOST", "localhost")
BUS_PORT = int(os.getenv("BUS_PORT", "5000"))
GATEWAY_NAME = "gatwy"

app = FastAPI(title="SCG Gateway", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Estado compartido entre threads ───────────────────────────────────────────

bus_socket: Optional[socket.socket] = None
bus_connected = threading.Event()
request_counter = 0
counter_lock = threading.Lock()

# Cola de requests: (payload_dict, response_queue)
request_queue: queue.Queue = queue.Queue()

# Respuestas pendientes: reply_id -> queue.Queue
pending_responses: dict[str, queue.Queue] = {}
pending_lock = threading.Lock()


# ── Thread del bus: mantiene conexión persistente ─────────────────────────────

def bus_listener():
    """Thread daemon que mantiene la conexión con el bus registrado."""
    global bus_socket, bus_connected

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((BUS_HOST, BUS_PORT))
            sock.settimeout(None)  # Bloqueante, manejado con select si fuera necesario

            # 1. REGISTRAR gateway en el bus
            init_content = b"sinit" + GATEWAY_NAME.encode()
            init_msg = str(len(init_content)).zfill(5).encode() + init_content
            sock.sendall(init_msg)

            # Leer confirmación
            ok_len = sock.recv(5)
            if ok_len:
                ok_amount = int(ok_len)
                ok_data = b""
                while len(ok_data) < ok_amount:
                    chunk = sock.recv(ok_amount - len(ok_data))
                    if not chunk:
                        break
                    ok_data += chunk
                print(f"[gateway] Registrado en bus: {ok_data[5:].decode()}")

            bus_socket = sock
            bus_connected.set()

            # 2. LOOP: procesar salientes + leer entrantes
            while True:
                # Enviar requests pendientes (non-blocking check)
                try:
                    payload, resp_queue = request_queue.get(timeout=0.05)
                    with counter_lock:
                        global request_counter
                        request_counter += 1
                        reply_id = f"{GATEWAY_NAME}-{request_counter}"
                        payload["reply_to"] = reply_id

                    payload_bytes = json.dumps(payload).encode("utf-8")
                    service_name = payload.pop("_service", "sgast")  # servicio destino
                    service_bytes = service_name.encode().ljust(5)[:5]
                    content = service_bytes + payload_bytes
                    message = str(len(content)).zfill(5).encode() + content
                    sock.sendall(message)

                    # Guardar queue para cuando llegue la respuesta
                    with pending_lock:
                        pending_responses[reply_id] = resp_queue

                except queue.Empty:
                    pass

                # Leer respuestas del bus (con timeout corto para no bloquear forever)
                sock.settimeout(0.1)
                try:
                    raw_len = sock.recv(5)
                    if raw_len:
                        amount = int(raw_len)
                        data = b""
                        while len(data) < amount:
                            chunk = sock.recv(amount - len(data))
                            if not chunk:
                                break
                            data += chunk

                        response = json.loads(data[5:].decode("utf-8"))
                        reply_id = response.get("reply_to", "")

                        # Entregar a quien esperaba
                        with pending_lock:
                            resp_queue = pending_responses.pop(reply_id, None)
                        if resp_queue:
                            resp_queue.put(response)
                except socket.timeout:
                    pass
                except Exception as e:
                    print(f"[gateway] Error leyendo respuesta: {e}")

        except Exception as e:
            print(f"[gateway] Reconectando al bus: {e}")
            bus_connected.clear()
            if bus_socket:
                try:
                    bus_socket.close()
                except:
                    pass
            bus_socket = None
            time.sleep(2)  # Esperar antes de reconectar


# Iniciar thread al arrancar
threading.Thread(target=bus_listener, daemon=True).start()


# ── Helper para endpoints: enviar y esperar respuesta ───────────────────────────

def call_service(service_name: str, payload: dict, timeout: float = 10.0) -> dict:
    """Envía un mensaje al bus por el thread persistente y espera respuesta."""
    if not bus_connected.wait(timeout=5.0):
        raise HTTPException(status_code=503, detail="Bus SOA no disponible (sin conexión).")

    resp_queue = queue.Queue()
    payload["_service"] = service_name  # Marcamos el servicio destino

    request_queue.put((payload, resp_queue))

    try:
        result = resp_queue.get(timeout=timeout)
        return result
    except queue.Empty:
        raise HTTPException(status_code=504, detail="Timeout esperando respuesta del bus.")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "bus": f"{BUS_HOST}:{BUS_PORT}",
        "connected": bus_connected.is_set(),
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login")
def login(req: LoginRequest):
    result = call_service("sauth", {
        "op": "login",
        "email": req.email,
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
    result = call_service("sauth", {
        "op": "verify",
        "token": token,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=401, detail=result.get("mensaje"))
    return result


# ── Gastos ──────────────────────────────────────────────────────────────────────

class GastoRequest(BaseModel):
    token: str
    monto: float
    concepto: str
    fecha: str
    comprobanteUrl: Optional[str] = None

@app.post("/gastos")
def crear_gasto(req: GastoRequest):
    result = call_service("sgast", {
        "op": "crear",
        "token": req.token,
        "monto": req.monto,
        "concepto": req.concepto,
        "fecha": req.fecha,
        "comprobanteUrl": req.comprobanteUrl,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


@app.get("/gastos")
def listar_gastos(token: str, estado: Optional[str] = None):
    payload = {
        "op": "listar",
        "token": token,
    }
    if estado is not None:
        payload["estado"] = estado
    result = call_service("sgast", payload)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


class CambioEstadoRequest(BaseModel):
    token: str
    estado: str

@app.patch("/gastos/{gasto_id}/estado")
def cambiar_estado(gasto_id: str, req: CambioEstadoRequest):
    result = call_service("sgast", {
        "op": "cambiar_estado",
        "token": req.token,
        "gasto_id": gasto_id,
        "estado": req.estado,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


# ── Saldos ────────────────────────────────────────────────────────────────────

@app.get("/saldos/mio")
def mi_saldo(token: str):
    result = call_service("ssald", {"op": "mi_saldo", "token": token})
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


@app.get("/saldos/{user_id}")
def saldo_operario(user_id: str, token: str):
    result = call_service("ssald", {
        "op": "saldo_operario",
        "token": token,
        "user_id": user_id,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=403, detail=result.get("mensaje"))
    return result


# ── Comprobantes ──────────────────────────────────────────────────────────────

@app.get("/comprobantes/{gasto_id}")
def url_comprobante(gasto_id: str, token: str):
    result = call_service("scomp", {
        "op": "obtener_url",
        "token": token,
        "gasto_id": gasto_id,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


# ── Reportes ──────────────────────────────────────────────────────────────────

@app.get("/reportes/consolidado")
def reporte_consolidado(
    token: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None
):
    payload = {
        "op": "consolidado",
        "token": token,
    }
    if fecha_desde:
        payload["fecha_desde"] = fecha_desde
    if fecha_hasta:
        payload["fecha_hasta"] = fecha_hasta
    result = call_service("srept", payload)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result