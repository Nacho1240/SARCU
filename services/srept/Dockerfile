FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/soa_lib.py .
COPY srept/srept_service.py .
ENV BUS_HOST=bus
ENV BUS_PORT=5000
CMD ["python3", "-u", "srept_service.py"]
