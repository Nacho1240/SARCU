# Dockerfile para desarrollo — Vite dev server con hot reload
FROM node:20-alpine

WORKDIR /app

# Instalar dependencias primero (cacheo de capas)
COPY package*.json ./
RUN npm install

# Copiar el resto del proyecto
COPY . .

EXPOSE 5173

# --host 0.0.0.0 es obligatorio para que Docker exponga el puerto hacia afuera
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
