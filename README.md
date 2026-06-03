# SCG-SOA — Sistema de Control de Gastos

Arquitectura SOA con bus TCP, servicios Python y frontend React + Vite.

## Estructura

```
scg-soa/
├── bus/              # Bus del profesor (agregar archivos aquí)
├── gateway/          # Puente HTTP → TCP (FastAPI)
├── frontend/         # PWA React + TypeScript + Vite
└── services/
    ├── shared/       # soa_lib.py compartida
    ├── sauth/        # Servicio de Autenticación
    ├── sgast/        # Servicio de Gastos
    ├── ssald/        # Servicio de Saldos
    ├── scomp/        # Servicio de Comprobantes
    └── srept/        # Servicio de Reportes
```

## Configuración inicial

```bash
# 1. Clonar el repo
git clone https://github.com/tu-usuario/scg-soa.git
cd scg-soa

# 2. Crear el archivo de variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Supabase

# 3. Agregar el bus del profesor
#    Copiar los archivos del bus a ./bus/ y actualizar ./bus/Dockerfile

# 4. Levantar todo
docker compose up --build
```

## Servicios disponibles

| Contenedor     | Puerto | Descripción                     |
|----------------|--------|---------------------------------|
| `scg-bus`      | 5000   | Bus SOA TCP (profesor)          |
| `scg-gateway`  | 8000   | REST API → TCP bridge           |
| `scg-frontend` | 5173   | PWA React                       |
| `scg-sauth`    | —      | Servicio Autenticación          |
| `scg-sgast`    | —      | Servicio Gastos                 |
| `scg-ssald`    | —      | Servicio Saldos                 |
| `scg-scomp`    | —      | Servicio Comprobantes           |
| `scg-srept`    | —      | Servicio Reportes               |

## Comandos útiles

```bash
# Ver logs de todos los servicios
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f sauth

# Reiniciar solo un servicio (útil mientras desarrollas)
docker compose restart sauth

# Reconstruir imagen de un servicio tras cambios
docker compose up --build sauth

# Detener todo
docker compose down
```

## Protocolo de mensajes

```
[5 bytes largo][5 bytes nombre servicio][payload JSON]
```

Nombres de servicio: `sauth`, `sgast`, `ssald`, `scomp`, `srept`

## URLs de desarrollo

- Frontend: http://localhost:5173
- Gateway API docs: http://localhost:8000/docs
- Gateway health: http://localhost:8000/health
