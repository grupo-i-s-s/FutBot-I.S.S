# FutBot

Base de desarrollo con React + Vite + Tailwind CSS, FastAPI, SQLAlchemy y PostgreSQL 18.
Docker Compose instala las dependencias y levanta los tres servicios.

## Guías para desarrollar en equipo

- [Frontend: archivos, dependencias y convenciones de React](frontend/README.md).
- [Backend: requirements, controllers, servicios, repositorios, modelos y schemas](backend/README.md).
- [Propuesta de ejecución y visualización de amistosos](docs/ejecucion_y_visualizacion_partidos.md).

Estas guías distinguen la base existente de la estructura propuesta para las próximas
funcionalidades e incluyen ejemplos de nombres y pautas para coordinar ambos equipos.

## Requisitos

- Git para clonar el repositorio.
- Docker Desktop iniciado en Windows/macOS, o Docker Engine con Compose en Linux.
- Usar contenedores Linux. En Windows, se recomienda el backend WSL 2.
- Internet para descargar imágenes y dependencias al construir o iniciar el frontend.

No hace falta instalar Node, Python ni PostgreSQL en la computadora. Las imágenes
seleccionan la arquitectura de la máquina (ARM64 o AMD64); no se fuerza una plataforma.
Este entorno usa servidores de desarrollo y credenciales de ejemplo, y publica sus
puertos solamente en la computadora local.

## Primer inicio

Desde la raíz del repositorio, copiar la configuración **solo si todavía no existe `.env`**:

```sh
cp .env.example .env
```

En Windows PowerShell se puede usar `Copy-Item .env.example .env`.
Luego ejecutar:

```sh
docker compose up --build -d --wait
```

Compose espera a que PostgreSQL esté disponible antes de iniciar FastAPI y a que
FastAPI pueda consultar la base antes de iniciar el frontend.

| Servicio | Dirección predeterminada |
| --- | --- |
| Aplicación React | http://localhost:5173 |
| Documentación interactiva de la API | http://localhost:8000/docs |
| API disponible | http://localhost:8000/health |
| API y base conectadas | http://localhost:8000/health/ready |
| PostgreSQL, para DataGrip u otro cliente | `localhost:5432` |

La pantalla inicial comprueba la conexión real con la API y PostgreSQL. La ruta
`/health/ready` devuelve `200 {"status":"ok","database":"ok"}` cuando puede
consultar la base, y `503` cuando no puede hacerlo.

Para PostgreSQL, usar el usuario, contraseña y base definidos en `.env`.
Si un puerto ya está ocupado, cambiar `FRONTEND_PORT`, `BACKEND_PORT` o
`POSTGRES_PORT` en `.env` y volver a ejecutar el comando de inicio. Los puertos
internos entre contenedores no cambian.

## Trabajo diario

```sh
# Iniciar y esperar a que estén listos
docker compose up -d --wait

# Ver estado y registros
docker compose ps
docker compose logs -f

# Detener y retirar contenedores, conservando los datos
docker compose down
```

Los cambios en `frontend/src/` y `backend/app/` se reflejan automáticamente.
El polling está habilitado para detectar cambios también en Docker Desktop y WSL.
No es necesario reconstruir por cada edición de código; los cambios en dependencias
o Dockerfiles sí requieren `docker compose up --build -d --wait`.

Los datos se guardan en el volumen `postgres_data` de este proyecto. **No usar
`docker compose down -v` para detener normalmente el entorno: elimina los datos.**
Cambiar el nombre de la carpeta del proyecto o usar otro nombre de proyecto Compose
crea otros volúmenes. Cambiar las credenciales en `.env` no cambia un usuario que ya
existe en un volumen de PostgreSQL; hay que actualizarlo en la base con sus credenciales
anteriores o reinicializar explícitamente una base descartable.


## Verificación

Con los servicios iniciados:

```sh
# Incluye una prueba de conexión contra PostgreSQL y una de fallo controlado
docker compose exec backend python -m pytest -q

# Verificar que React se puede compilar
docker compose exec frontend npm run build
```

## Dependencias

`package-lock.json` y los dos `requirements*.txt` fijan las versiones resueltas.
El frontend ejecuta `npm ci` al iniciar para mantener su volumen de dependencias
sincronizado con el lockfile, sin usar los módulos del sistema anfitrión.

Para agregar una dependencia del frontend:

```sh
docker compose exec frontend npm install --save-exact nombre-del-paquete
```

Para modificar dependencias Python, editar `backend/requirements.in` o
`backend/requirements-dev.in`. Regenerar los archivos resueltos con `uv` en un
contenedor temporal (no hace falta instalarlo en la computadora):

```sh
docker compose run --rm --no-deps backend sh -c "pip install uv && uv pip compile --python-version 3.12 --universal requirements.in -o requirements.txt && uv pip compile --python-version 3.12 --universal requirements-dev.in -o requirements-dev.txt"
docker compose up --build -d --wait
```

Las imágenes base siguen las ramas Node 22, Python 3.12 y PostgreSQL 18 y pueden recibir
actualizaciones de parche; los lockfiles fijan las bibliotecas de la aplicación.
Versionar los archivos de dependencias y `.env.example`. `.env` contiene la configuración
de cada integrante y está excluido de nuevos archivos por `.gitignore`; si ya estaba
agregado al índice de Git, esa exclusión no lo retira automáticamente.

Referencias: [Vite](https://vite.dev/guide/),
[FastAPI en Docker](https://fastapi.tiangolo.com/deployment/docker/),
[sesiones de SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) y
[volúmenes de la imagen PostgreSQL 18](https://hub.docker.com/_/postgres).
