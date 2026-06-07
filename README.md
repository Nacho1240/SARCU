<div align="center">

# 💰 SCG-SOA — Sistema de Control de Gastos

**Arquitectura SOA distribuida** con bus de mensajes TCP, microservicios Python y frontend PWA React + Vite.

[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://www.docker.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/Gateway-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://www.python.org/)
[![Supabase](https://img.shields.io/badge/Backend-Supabase-3ECF8E?logo=supabase)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Arquitectura](#-arquitectura)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Requisitos Previos](#-requisitos-previos)
- [Configuración Inicial](#-configuración-inicial)
- [Variables de Entorno](#-variables-de-entorno)
- [Servicios Disponibles](#-servicios-disponibles)
- [Comandos Útiles](#-comandos-útiles)
- [Protocolo de Mensajes](#-protocolo-de-mensajes)
- [URLs de Desarrollo](#-urls-de-desarrollo)
- [Contribuidores](#-contribuidores)
- [Solución de Problemas](#-solución-de-problemas)

---

## 📝 Descripción

SCG-SOA es un **Sistema de Control de Gastos** construido sobre una arquitectura orientada a servicios (SOA). El sistema permite gestionar gastos personales, saldos, comprobantes y generar reportes, todo comunicado a través de un bus de mensajes TCP centralizado.

### Características principales
- 🔐 **Autenticación** segura vía Supabase Auth
- 💸 **Registro y categorización** de gastos
- 📊 **Reportes** exportables a PDF
- 📸 **Adjuntar comprobantes** con compresión de imágenes
- 🌐 **PWA** lista para instalar en dispositivos móviles
- 🐳 **Despliegue** 100% containerizado con Docker Compose

---

## 🏗️ Arquitectura

```
┌─────────────────┐      HTTP        ┌─────────────────┐
│   🌐 Frontend   │ ◄──────────────► │   🚪 Gateway    │
│  React + Vite   │                  │    FastAPI      │
│   (Puerto 5173) │                  │   (Puerto 8000) │
└─────────────────┘                  └────────┬────────┘
                                              │
                                              │ TCP
                                              ▼
┌─────────────────────────────────────────────────────────┐
│                      🚌 Bus SOA TCP                      │
│                      (Puerto 5000)                      │
└─────────────────────────────────────────────────────────┘
         │         │         │         │         │
         ▼         ▼         ▼         ▼         ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │  sauth │ │  sgast │ │  ssald │ │  scomp │ │  srept │
    │  Auth  │ │ Gastos │ │ Saldos │ │ Compr. │ │Reportes│
    └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
         │         │         │         │         │
         └─────────┴─────────┴─────────┴─────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   🗄️ Supabase   │
                    │  (PostgreSQL)   │
                    └─────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Descripción |
|------|------------|-------------|
| **Frontend** | React 19 + TypeScript + Vite | PWA interactiva y responsive |
| **UI** | Tailwind CSS v4 + Radix UI | Estilos modernos y componentes accesibles |
| **Gateway** | FastAPI | Puente HTTP ↔ TCP con documentación auto-generada |
| **Servicios** | Python 3.12 | Microservicios independientes y especializados |
| **Bus** | TCP Socket (profesor) | Bus de mensajes SOA centralizado |
| **Base de datos** | Supabase (PostgreSQL) | Auth, storage y base de datos relacional |
| **PDF** | jsPDF + AutoTable | Generación de reportes en PDF |
| **Imágenes** | browser-image-compression | Compresión de comprobantes en el cliente |
| **Contenedores** | Docker + Docker Compose | Orquestación de todos los servicios |

---

## 📁 Estructura del Proyecto

```
scg-soa/
├── 📂 bus/                    # Bus de mensajes SOA TCP (archivos del profesor)
│   └── Dockerfile
├── 📂 gateway/                # 🚪 Puente HTTP → TCP (FastAPI)
│   ├── main.py
│   └── Dockerfile
├── 📂 frontend/               # 🌐 PWA React + TypeScript + Vite
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── 📂 services/
│   ├── 📂 shared/             # 📚 soa_lib.py (librería compartida)
│   ├── 📂 sauth/              # 🔐 Servicio de Autenticación
│   ├── 📂 sgast/              # 💸 Servicio de Gastos
│   ├── 📂 ssald/              # 💰 Servicio de Saldos
│   ├── 📂 scomp/              # 📄 Servicio de Comprobantes
│   └── 📂 srept/              # 📊 Servicio de Reportes
├── docker-compose.yml         # 🐳 Orquestación de contenedores
├── .env.example               # 📋 Plantilla de variables de entorno
└── README.md                  # 📖 Este archivo
```

---

## ✅ Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- [Docker](https://docs.docker.com/get-docker/) (v24.0+ recomendado)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.20+ recomendado)
- Una cuenta en [Supabase](https://supabase.com/) (gratuita)

---

## 🚀 Configuración Inicial

### 1. Clonar el repositorio

```bash
git clone https://github.com/Nacho1240/SARCU.git
cd SARCU
```

### 2. Configurar variables de entorno

```bash
# Copiar la plantilla
cp .env.example .env

# Editar .env con tus credenciales de Supabase
# (Ver sección [Variables de Entorno](#-variables-de-entorno) abajo)
```

### 3. Agregar el bus del profesor

> ⚠️ **Importante:** El bus SOA TCP es proporcionado por el profesor. Copia los archivos del bus a `./bus/` y asegúrate de que `./bus/Dockerfile` esté correctamente configurado.

```bash
# Ejemplo: copiar archivos del bus (ajusta según tu caso)
cp /ruta/al/bus/* ./bus/
```

### 4. Levantar todos los servicios

```bash
# Primera vez (construye las imágenes)
docker compose up --build

# Modo detached (segundo plano)
docker compose up --build -d
```

### 5. Verificar que todo funciona

- Abre el frontend: http://localhost:5173
- Revisa la documentación de la API: http://localhost:8000/docs
- Health check del gateway: http://localhost:8000/health

---

## 🔑 Variables de Entorno

Copia `.env.example` a `.env` y completa los siguientes valores:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SUPABASE_URL` | URL de tu proyecto Supabase | `https://tuproyecto.supabase.co` |
| `SUPABASE_KEY` | Clave anónima (anon key) de Supabase | `eyJhbGciOiJIUzI1NiIs...` |
| `BUS_HOST` | Host del bus SOA *(solo si no usas Docker)* | `localhost` |
| `BUS_PORT` | Puerto del bus SOA *(solo si no usas Docker)* | `5000` |

### ¿Cómo obtener tus credenciales de Supabase?

1. Ve a [supabase.com](https://supabase.com/) y accede a tu proyecto
2. Navega a **Project Settings → API**
3. Copia:
   - **URL** → `SUPABASE_URL`
   - **anon / public** key → `SUPABASE_KEY`

---

## 🐳 Servicios Disponibles

| Contenedor | Puerto Expuesto | Puerto Interno | Descripción | Dependencias |
|------------|-----------------|----------------|-------------|--------------|
| `scg-bus` | `5000` | `5000` | 🚌 Bus SOA TCP (profesor) | — |
| `scg-gateway` | `8000` | `8000` | 🚪 REST API → TCP bridge (FastAPI) | `bus` |
| `scg-frontend` | `5173` | `5173` | 🌐 PWA React + Vite | `gateway` |
| `scg-sauth` | — | — | 🔐 Servicio de Autenticación | `bus` |
| `scg-sgast` | — | — | 💸 Servicio de Gastos | `bus` |
| `scg-ssald` | — | — | 💰 Servicio de Saldos | `bus` |
| `scg-scomp` | — | — | 📄 Servicio de Comprobantes | `bus` |
| `scg-srept` | — | — | 📊 Servicio de Reportes | `bus` |

> **Nota:** Los servicios internos (`sauth`, `sgast`, `ssald`, `scomp`, `srept`) no exponen puertos directamente. Se comunican exclusivamente a través del bus TCP y son accesibles vía el Gateway en el puerto `8000`.

---

## 🧰 Comandos Útiles

### Gestión general

```bash
# Levantar todo (construir imágenes)
docker compose up --build

# Levantar en segundo plano
docker compose up --build -d

# Detener todos los servicios
docker compose down

# Detener y eliminar volúmenes
docker compose down -v
```

### Logs y monitoreo

```bash
# Ver logs de todos los servicios en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f sauth

# Ver logs de los últimos 50 líneas
docker compose logs --tail=50 gateway
```

### Desarrollo y reinicio

```bash
# Reiniciar un solo servicio (útil mientras desarrollas)
docker compose restart sauth

# Reconstruir imagen de un servicio tras cambios
docker compose up --build sauth

# Reconstruir solo el frontend
docker compose up --build frontend

# Ejecutar shell dentro de un contenedor
docker compose exec gateway bash
```

---

## 📡 Protocolo de Mensajes

La comunicación entre el Gateway y los microservicios utiliza un protocolo binario sobre TCP:

```
[5 bytes largo][5 bytes nombre servicio][payload JSON]
```

| Campo | Longitud | Descripción |
|-------|----------|-------------|
| `largo` | 5 bytes | Longitud del payload JSON (padding con ceros) |
| `servicio` | 5 bytes | Nombre del servicio destino |
| `payload` | variable | Cuerpo del mensaje en formato JSON |

### Nombres de servicio válidos

| Servicio | Descripción |
|----------|-------------|
| `sauth` | Autenticación (login, registro, JWT) |
| `sgast` | Gestión de gastos (CRUD) |
| `ssald` | Consulta y actualización de saldos |
| `scomp` | Subida y gestión de comprobantes |
| `srept` | Generación de reportes y estadísticas |

---

## 🌐 URLs de Desarrollo

Una vez que todo esté levantado, estas son las URLs locales disponibles:

| URL | Descripción |
|-----|-------------|
| http://localhost:5173 | 🌐 **Frontend** — Aplicación React |
| http://localhost:8000/docs | 📚 **Swagger UI** — Documentación interactiva de la API |
| http://localhost:8000/redoc | 📖 **ReDoc** — Documentación alternativa de la API |
| http://localhost:8000/health | 💓 **Health Check** — Estado del gateway y servicios |

---

## 👥 Contribuidores

Gracias a estas personas por contribuir a este proyecto:

| [<img src="https://github.com/DHat3r.png?size=80" width="80" height="80" style="border-radius:50%">](https://github.com/DHat3r) | [<img src="https://github.com/Nacho1240.png?size=80" width="80" height="80" style="border-radius:50%">](https://github.com/Nacho1240) | [<img src="https://github.com/Rafaas18.png?size=80" width="80" height="80" style="border-radius:50%">](https://github.com/Rafaas18) |
|:---:|:---:|:---:|
| **[DHat3r](https://github.com/DHat3r)** | **[Nacho1240](https://github.com/Nacho1240)** | **[Rafaas18](https://github.com/Rafaas18)** |
| 15 contribuciones | 13 contribuciones | 8 contribuciones |

---

## 🛠️ Solución de Problemas

### El bus no se conecta
```bash
# Verificar que el bus esté saludable
docker compose ps
# Si el bus está en estado (unhealthy), revisa los archivos en ./bus/
```

### Un servicio no responde
```bash
# Reiniciar el servicio específico
docker compose restart <servicio>

# Ver logs detallados
docker compose logs -f <servicio>
```

### Error de conexión a Supabase
- Verifica que `SUPABASE_URL` y `SUPABASE_KEY` en `.env` sean correctos
- Asegúrate de que el proyecto Supabase esté activo
- Si cambiaste `.env`, reconstruye los contenedores: `docker compose up --build`

### Puerto ya en uso
```bash
# Ver qué proceso usa el puerto
lsof -i :5000   # o :8000, :5173

# Matar el proceso o cambiar el puerto en docker-compose.yml
```

### Frontend no carga cambios
```bash
# El frontend usa hot-reload con volumen montado
# Si no funciona, reinicia:
docker compose restart frontend
```

---

<div align="center">

**[⬆ Volver al inicio](#-scg-soa--sistema-de-control-de-gastos)**

<br>

Hecho con ❤️ por el equipo SCG-SOA

</div>
