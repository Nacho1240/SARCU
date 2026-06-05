import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

servicios = {}
lock = threading.Lock()


def send_raw(sock, destino, payload):
    content = destino.encode() + payload.encode()
    length = str(len(content)).zfill(5)
    sock.sendall(length.encode() + content)


def receive_raw(sock):
    raw_len = sock.recv(5)

    if not raw_len:
        return None

    try:
        amount = int(raw_len)
    except ValueError:
        return None

    data = b""

    while len(data) < amount:
        chunk = sock.recv(amount - len(data))

        if not chunk:
            return None

        data += chunk

    return data


def client_handler(sock, addr):
    servicio_registrado = None

    try:
        while True:
            data = receive_raw(sock)

            if not data:
                break

            destino = data[:5].decode()
            payload = data[5:].decode()

            # =========================
            # SOLO REGISTRO IMPORTA
            # =========================
            if destino == "sinit":
                nombre_servicio = payload
                servicio_registrado = nombre_servicio

                with lock:
                    servicios[nombre_servicio] = sock

                print(f"[BUS] Servicio registrado: {nombre_servicio} desde {addr}")

                send_raw(sock, "sinit", "OK")
                continue

            # 🔇 ignorar todo lo que no venga de un servicio registrado
            if servicio_registrado is None:
                continue

            # =========================
            # ROUTING REAL
            # =========================
            with lock:
                destino_sock = servicios.get(destino)

            if destino_sock:
                try:
                    destino_sock.sendall(
                        str(len(data)).zfill(5).encode() + data
                    )
                    print(f"[BUS] {servicio_registrado} → {destino}")
                except Exception as e:
                    print(f"[BUS] Error reenviando: {e}")
            else:
                print(f"[BUS] Servicio '{destino}' no registrado")

    except Exception as e:
        if servicio_registrado:
            print(f"[BUS] Error en servicio {servicio_registrado}: {e}")
        else:
            print(f"[BUS] Error cliente {addr}: {e}")

    finally:
        if servicio_registrado:
            print(f"[BUS] Servicio desconectado: {servicio_registrado}")

            with lock:
                servicios.pop(servicio_registrado, None)

        sock.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))
    server.listen()

    print(f"[BUS] Escuchando en {HOST}:{PORT}")

    while True:
        client, addr = server.accept()

        threading.Thread(
            target=client_handler,
            args=(client, addr),
            daemon=True
        ).start()


if __name__ == "__main__":
    main()