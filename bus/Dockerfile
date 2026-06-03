FROM python:3.11-slim

WORKDIR /app

# ──────────────────────────────────────────────────────────────────────────────
# INSTRUCCIÓN: Copia aquí los archivos del bus del profesor
#   - El archivo principal del bus (ej: bus.py)
#   - Cualquier dependencia que requiera
#
# Luego descomenta las líneas correspondientes:
# ──────────────────────────────────────────────────────────────────────────────

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY bus.py .

EXPOSE 5000

# CMD ["python3", "-u", "bus.py"]

# Mientras no tengas el bus del profesor, este contenedor solo mantiene el puerto abierto
CMD ["python3", "-u", "-c", "import socket,time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(('0.0.0.0',5000)); s.listen(); print('Bus placeholder escuchando en :5000'); [time.sleep(1) for _ in iter(int,1)]"]
