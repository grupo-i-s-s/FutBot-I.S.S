# Backend de FutBot

Guía para desarrollar la API en equipo con **FastAPI, SQLAlchemy y PostgreSQL**.
Las convenciones de este documento son la propuesta de trabajo del proyecto;
si el equipo cambia una, debe actualizar esta guía en la misma entrega.

Para preparar el entorno completo, seguir el [README principal](../README.md).
Todos los comandos Docker de esta guía se ejecutan desde la **raíz del repositorio**.

## 1. Qué hace cada archivo actual

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| `Dockerfile` | Prepara Python 3.12, instala dependencias y arranca Uvicorn con recarga automática. |
| `.dockerignore` | Excluye archivos locales del contexto de construcción de Docker. No reemplaza a `.gitignore`. |
| `requirements.in` | Lista las dependencias directas necesarias para ejecutar la API. Es un archivo que editamos. |
| `requirements.txt` | Lista resuelta de dependencias de ejecución, con versiones fijas, incluidas las transitivas. Se genera. |
| `requirements-dev.in` | Agrega herramientas de desarrollo y pruebas e incluye las dependencias de ejecución. Es un archivo que editamos. |
| `requirements-dev.txt` | Lista resuelta completa para desarrollar y probar. Se genera; el Dockerfile actual instala este archivo. |
| `app/__init__.py` | Identifica `app` como paquete Python; puede permanecer vacío. |
| `app/main.py` | Crea la aplicación FastAPI, define su ciclo de vida y contiene las rutas de salud actuales. |
| `app/database.py` | Configura el motor, la fábrica de sesiones, la base ORM y la dependencia de sesión por petición. |
| `tests/test_health.py` | Prueba que la API responde, que consulta PostgreSQL y que informa una falla de conexión. |
| `__pycache__/`, `.pytest_cache/` | Archivos temporales generados por Python y pytest. No se versionan. |

**FastAPI** recibe peticiones y produce respuestas HTTP. **Uvicorn** es el servidor
que ejecuta la aplicación. **SQLAlchemy** gestiona consultas y el mapeo entre objetos
Python y tablas (ORM). **Psycopg** es el controlador que conecta Python con PostgreSQL.
**Pydantic** valida y serializa los datos de entrada y salida de FastAPI.

## 2. Cómo funcionan los requirements

Una dependencia **directa** es elegida por el equipo, por ejemplo SQLAlchemy.
Una **transitiva** es requerida por otra biblioteca. Los `.in` expresan las decisiones
del proyecto y los `.txt` guardan la resolución que deben instalar todas las máquinas.
`requirements` significa aquí «dependencias Python», no requerimientos funcionales del sprint.

```text
requirements.in ── uv pip compile ──> requirements.txt
                                           │
                                  incluido mediante -r
                                           ▼
requirements-dev.in ── uv pip compile ──> requirements-dev.txt
```

Ejemplos tomados de los archivos actuales:

| Sintaxis | Significado |
| --- | --- |
| `sqlalchemy==2.1.1` | Instalar esa versión exacta. |
| `psycopg[binary]==3.3.6` | Instalar Psycopg con el extra `binary`, que agrega su distribución binaria. |
| `uvicorn[standard]==0.54.0` | Incluir las dependencias opcionales del conjunto `standard`. |
| `-r requirements.txt` | Incluir las dependencias de ese otro archivo. No es el nombre de un paquete. |
| `; sys_platform == 'win32'` | Instalar esa entrada solo cuando se cumple la condición de plataforma. |
| `# via fastapi` | Comentario generado que explica por qué aparece una dependencia. |

Usar `requirements.in` para bibliotecas necesarias al ejecutar la aplicación y
`requirements-dev.in` para herramientas como pytest. Si el código del proyecto
importa directamente una biblioteca que hoy llega de forma transitiva, declararla
también como directa al incorporar ese uso; por ejemplo, al crear esquemas propios con Pydantic.

### Agregar, quitar o actualizar un paquete

1. Editar el `.in` correspondiente. Para actualizar una dependencia directa, cambiar
   su versión exacta allí; para quitarla, eliminar la entrada.
2. Regenerar primero las dependencias de ejecución y luego las de desarrollo:

```sh
docker compose run --rm --no-deps backend sh -c "pip install uv && uv pip compile --python-version 3.12 --universal requirements.in -o requirements.txt && uv pip compile --python-version 3.12 --universal requirements-dev.in -o requirements-dev.txt"
```

3. Reconstruir y verificar:

```sh
docker compose up --build -d --wait
docker compose exec backend python -m pytest -q
```

El comando de resolución usa la imagen backend ya construida en la preparación
inicial e instala `uv` en un contenedor temporal. Los archivos resultantes se escriben
en la carpeta compartida del proyecto. `--python-version 3.12` fija la versión objetivo
y `--universal` genera una resolución que contempla varias plataformas; no prueba
la aplicación en todos los sistemas.

Versionar los cambios de `.in` y `.txt` juntos. No editar los `.txt` a mano ni reemplazarlos
por un `pip freeze` de un entorno personal. Un `pip install` ejecutado manualmente en
un contenedor tampoco deja registrada una dependencia del proyecto.

El compilador conserva versiones ya resueltas cuando son compatibles. Una actualización
transitiva deliberada puede requerir `--upgrade-package nombre-del-paquete` en la
resolución correspondiente; revisar el cambio, regenerar después la lista de desarrollo
y probarlo. No actualizar todas las dependencias como efecto secundario de otra tarea.
[Referencia de resolución de dependencias con uv](https://docs.astral.sh/uv/pip/compile/).

## 3. Convenciones de nombres y estilo

Usar inglés en identificadores y español en documentación y mensajes para el usuario.
Mantener el vocabulario compartido: `player`, `club`, `league`, `match`, `behaviour`.
No mezclar `behaviour` y `behavior` para el mismo concepto.

| Elemento | Convención | Ejemplo |
| --- | --- | --- |
| Archivos y carpetas Python | Minúsculas, `snake_case` | `friendly_matches.py`, `services/` |
| Variables, atributos y funciones | `snake_case` | `club_id`, `create_player()` |
| Clases | `PascalCase` | `Player`, `PlayerCreate`, `PlayerRead` |
| Constantes de módulo y variables de entorno | `UPPER_SNAKE_CASE` | `DEFAULT_TIMEOUT_SECONDS`, `POSTGRES_DB` |
| Booleanos | Condición explícita | `is_available`, `has_opponent`, `can_join` |
| Tablas futuras | Plural en `snake_case` | `players`, `friendly_matches` |
| Claves primarias y foráneas | `id` y entidad singular + `_id` | `id`, `club_id` |
| Módulos de rutas | Recurso en plural | `players.py`, `leagues.py` |
| Pruebas | `test_` + comportamiento | `test_create_player_rejects_invalid_pacss` |
| Campos JSON públicos | Nombres exactos del contrato, usualmente `camelCase` | `clubId`, `behaviourId` |
| Rutas HTTP | Nombres del contrato, minúsculas y guiones cuando corresponda | `/players`, `/friendly-matches` |

Usar cuatro espacios, comillas dobles, UTF-8 y fin de línea LF. Como guía de legibilidad,
apuntar a líneas de hasta 100 caracteres; no reformatear archivos ajenos por ese motivo.
Agregar anotaciones de tipo a funciones nuevas y docstrings cuando la responsabilidad
o las reglas no sean evidentes. Los comentarios deben explicar decisiones, no repetir
lo que ya dice una instrucción.

Ordenar imports: biblioteca estándar, bibliotecas externas y módulos propios, separados
por líneas en blanco. Usar imports desde `app`, por ejemplo `from app.database import get_db`.
Evitar `import *` y módulos llamados `fastapi.py`, `sqlalchemy.py` o `typing.py`, porque
pueden ocultar paquetes reales. `SessionLocal` conserva el nombre de la fábrica ya existente.

## 4. Estructura al agregar funcionalidades

El árbol siguiente es una **estructura propuesta para crecer**. Hoy solo existen
los archivos de la sección 1. Crear los módulos según la necesidad de cada tarea,
sin agregar capas vacías ni mover código ajeno como parte de un cambio funcional.

```text
app/
  __init__.py
  main.py                        # Aplicación, middleware y registro de routers
  database.py                    # Motor, sesiones y Base
  api/
    __init__.py
    dependencies.py              # Dependencias HTTP comunes, p. ej. usuario autenticado
    routes/
      __init__.py
      players.py                 # APIRouter del recurso
      leagues.py
  schemas/
    __init__.py
    player.py                    # PlayerCreate, PlayerRead: datos de entrada/salida
  models/
    __init__.py
    player.py                    # Player: tabla y relaciones ORM
  services/
    __init__.py
    players.py                   # Casos de uso y reglas de jugadores
  core/
    __init__.py
    config.py                    # Configuración común, cuando crezca
    errors.py                    # Errores funcionales compartidos
tests/
  test_health.py                 # Pruebas existentes
  unit/
    test_players.py              # Reglas aisladas
  integration/
    test_players_api.py          # HTTP, persistencia y transacciones
```

Una **ruta** traduce HTTP a una operación, obtiene las dependencias y define la respuesta.
Un **schema** describe y valida los datos que entran o salen. Un **modelo** representa
una tabla. Un **servicio** ejecuta un caso de uso y sus reglas. Evitar concentrar consultas,
validación, autenticación y transacciones en `main.py`.

Dirección de dependencias: rutas → servicios → modelos/base de datos. Los servicios
no importan routers ni `app.main`; los modelos no dependen de HTTP. Los schemas no son
modelos ORM: por ejemplo, `PlayerCreate` puede admitir solo campos de alta y `PlayerRead`
incluir el ID generado. Si crecen las consultas compartidas, evaluar una capa de repositorios;
no es obligatoria para cada operación simple.

## 5. Sesiones, escrituras y esquema de base de datos

`engine` administra conexiones. `SessionLocal` crea sesiones y `get_db` entrega una
por petición, cerrándola al finalizar. `Base` es la clase de la que heredarán los modelos.
No crear motores ni sesiones globales adicionales por funcionalidad.

La configuración actual es **sincrónica**: usar funciones `def` en rutas que realizan
consultas con esta `Session`. No introducir consultas bloqueantes en `async def`
ni mezclar `AsyncSession` sin coordinar un cambio de acceso a datos.

El servicio que representa el caso de uso completo es el responsable de la transacción:
confirmar una vez cuando toda la operación termine y hacer rollback si falla.
Las funciones auxiliares no deben hacer commits parciales. Por ejemplo, crear cuenta,
club y jugadores iniciales debe ser una única operación atómica. `get_db` no hace
commit automáticamente; cerrar una sesión no guarda los cambios pendientes.

Usar consultas parametrizadas de SQLAlchemy; no concatenar entradas del usuario en SQL.
Aplicar restricciones de unicidad y claves foráneas en la base además de las validaciones
de aplicación. Una comprobación previa por sí sola no evita carreras entre peticiones.

Todavía no hay modelos del dominio ni Alembic instalado. Antes de introducir el esquema
compartido, incorporar migraciones versionadas. No usar cambios manuales en DataGrip
como único registro del esquema ni confiar en `create_all()` para actualizar tablas existentes.
Si se incorpora Alembic, sus archivos y comandos deberán añadirse a esta guía.

## 6. Contrato con el frontend

Consultar el [contrato de Sprint 2](../docs/api_sprint_2.md), que sigue marcado como
**propuesta**. Coordinar y documentar ajustes de rutas, campos o errores antes de integrarlos.
Actualmente solo están implementadas las rutas `/health` y `/health/ready`; esta sección
describe convenciones para los futuros endpoints funcionales.

Mantener `snake_case` en Python y los nombres públicos del contrato en JSON mediante
aliases explícitos de Pydantic. Ejemplo ilustrativo para un esquema futuro:

```python
from pydantic import BaseModel, ConfigDict, Field


class ClubAvailabilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    friendly_available: bool = Field(alias="friendlyAvailable")


payload = ClubAvailabilityUpdate.model_validate({"friendlyAvailable": True})
assert payload.friendly_available is True
assert payload.model_dump(by_alias=True) == {"friendlyAvailable": True}
```

Declarar los schemas de respuesta en FastAPI y verificar en pruebas los nombres
serializados. No exponer directamente todos los atributos del ORM. Si el esquema
se construye desde un modelo ORM, configurar y probar también esa conversión;
el ejemplo anterior solo muestra una entrada JSON.
[Referencia de aliases de Pydantic](https://docs.pydantic.dev/latest/concepts/alias/).

El contrato propone listas `{ "items": [...] }`, fechas con zona en UTC y errores
`{ "error": { "code": "...", "message": "...", "fields": {} } }`.
Mantener siempre `fields` como objeto y no filtrar contraseñas, tokens ni detalles SQL.
Validar permisos y derivar el club de la identidad autenticada; no confiar en un
`clubId` enviado por el cliente para demostrar pertenencia.

Las validaciones funcionales y de campos deben usar `400` según la propuesta; FastAPI
usa normalmente `422` para errores de validación. **La adaptación global a `400` y al
formato común aún no está implementada** y deberá incluirse al desarrollar las rutas
funcionales. También respetar `401`, `403`, `404` y `409` según el caso del contrato,
y respuestas `204` sin cuerpo. Las rutas de salud mantienen sus respuestas técnicas actuales.

El prefijo `/api` pertenece al proxy de Vite: una petición del navegador a `/api/players`
llega al backend como `/players`. No agregar ese prefijo a los routers por duplicado.

## 7. Configuración y datos locales

Las variables provienen del `.env` de la raíz a través de Compose. Actualmente
`database.py` lee `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`
y `POSTGRES_PORT`. Dentro de Docker, el servidor es `db` y el puerto es `5432`;
el puerto publicado en la computadora puede ser distinto.

Agregar nuevas variables compartidas a `.env.example`, con una explicación y valores
de ejemplo sin secretos, y pasarlas explícitamente al servicio en `compose.yaml`.
No dejar valores personales en el código. `.env` no debe subirse a Git; si ya estaba
en el índice antes de agregarlo a `.gitignore`, revisarlo antes de preparar el commit.

Los datos persisten en un volumen de Docker. `docker compose down` los conserva;
`docker compose down -v` los elimina. No usar el segundo comando como solución rutinaria
ante errores de conexión ni para aplicar cambios de esquema.

## 8. Pruebas y revisión

Con PostgreSQL y backend iniciados:

```sh
docker compose exec backend python -m pytest -q
docker compose logs --tail=100 backend
```

La prueba actual de disponibilidad consulta la base real mediante `SELECT 1` y no
escribe datos. Las pruebas de persistencia futuras deberán usar una base exclusiva
de pruebas y datos aislados, con limpieza o rollback; esa infraestructura todavía
no está configurada. No ejecutar pruebas que borren tablas sobre la base de trabajo.

Para cada nueva regla o endpoint, cubrir el caso válido, entradas inválidas y los
errores de permiso o estado que correspondan. En escrituras, comprobar que un rechazo
no deja cambios parciales. Probar las reglas delicadas en concurrencia cuando aplique,
por ejemplo una única plaza disponible. Usar nombres de pruebas que expresen el
comportamiento y datos sintéticos; no depender del orden de ejecución.

Todavía no hay Ruff, Black ni una verificación automática de estilo configurados.
Las convenciones de esta guía se revisan manualmente hasta incorporar esas herramientas
en una tarea compartida.

## 9. Coordinación del equipo

1. Revisar ticket, contrato y módulo existente antes de crear otro archivo que resuelva
   lo mismo. Acordar con frontend un ejemplo de entrada, éxito y error.
2. Trabajar en una rama por tarea; por ejemplo, `feat/<ticket>-create-player`, reemplazando
   `<ticket>` por el identificador real. Mantener nombres descriptivos en minúsculas y guiones.
3. Separar cambios funcionales de reorganizaciones amplias. No sobrescribir trabajo
   ajeno ni introducir nuevas bibliotecas o capas sin justificar su uso.
4. Usar commits `feat: ...`, `fix: ...`, `docs: ...`, `test: ...` o `refactor: ...`
   según el cambio. Incluir el ticket real cuando corresponda.
5. Antes de pedir revisión, actualizar contratos, ejemplos y dependencias afectados;
   explicar cómo probar, qué pruebas pasaron y qué está pendiente.
6. Resolver conflictos de dependencias en los `.in` y regenerar ambos `.txt` en orden.
   No resolverlos descartando silenciosamente las dependencias de otro integrante.

Guía relacionada: [convenciones del frontend](../frontend/README.md).
