FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias (contexto de build es services/)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar librería compartida y el servicio
COPY shared/soa_lib.py .
COPY sauth/sauth_service.py .

ENV BUS_HOST=bus
ENV BUS_PORT=5000

CMD ["python3", "-u", "sauth_service.py"]
