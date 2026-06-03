"""
soa_lib.py — Librería de comunicación con el Bus SOA (TCP)
Versión extendida: lee BUS_HOST / BUS_PORT desde variables de entorno
y reintenta la conexión automáticamente (útil en Docker).
"""
import os
import socket
import time


def connect_to_bus(host: str = None, port: int = None, retries: int = 10, delay: float = 2.0):
    """
    Conecta al bus SOA via TCP.
    Lee BUS_HOST / BUS_PORT del entorno si no se pasan como argumento.
    Reintenta hasta `retries` veces con `delay` segundos entre intentos.
    """
    host = host or os.getenv("BUS_HOST", "localhost")
    port = port or int(os.getenv("BUS_PORT", "5000"))

    for intento in range(1, retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            print(f"[soa_lib] Conectado a {host}:{port}")
            return sock
        except (ConnectionRefusedError, OSError) as e:
            print(f"[soa_lib] Intento {intento}/{retries} — bus no disponible ({e}). Reintentando en {delay}s...")
            sock.close()
            time.sleep(delay)

    raise ConnectionError(f"No se pudo conectar al bus en {host}:{port} tras {retries} intentos.")


def send_message(sock, service_name: str, payload: str):
    """
    Envía un mensaje al bus con el formato del protocolo SOA:
      [5 bytes largo][5 bytes nombre servicio][N bytes payload]
    """
    content = service_name.encode() + payload.encode()
    length   = str(len(content)).zfill(5)
    message  = length.encode() + content
    sock.sendall(message)


def receive_message(sock) -> bytes | None:
    """
    Recibe un mensaje completo del bus.
    Devuelve bytes con formato [5 bytes nombre][N bytes payload], o None si se cerró.
    """
    raw_len = sock.recv(5)
    if not raw_len:
        return None
    try:
        amount_expected = int(raw_len)
    except ValueError:
        return None

    data = b""
    while len(data) < amount_expected:
        chunk = sock.recv(amount_expected - len(data))
        if not chunk:
            break
        data += chunk
    return data
