# API de FutBot

FastAPI publica el contrato de la versión en ejecución en `/openapi.json` y la interfaz de consulta en `/docs`. El navegador agrega `/api` a las solicitudes HTTP y WebSocket. Vite retira ese prefijo al enviarlas al backend.

Las rutas de la API usan recursos en inglés y segmentos en kebab-case, como `/clubs`, `/friendly-matches` y `/matches/{match_id}/live-requests`. Los identificadores de recurso van en el path. Las acciones que no son lecturas o reemplazos de un recurso, como `join` y `start`, usan `POST`. Los contratos nuevos usan camelCase en JSON. Los campos históricos que siguen vigentes se detallan en OpenAPI.

Los endpoints privados requieren sesión por cookie `FutBotSession`. Salud, registro, verificación, reenvío, inicio y cierre de sesión se pueden llamar sin sesión previa. Las escrituras requieren un `Origin` permitido y el encabezado `X-FutBot-Request: 1`. Los errores de aplicación devuelven `error.code`, `error.message` y `error.fields`, con `error.diagnostics` cuando corresponde. La validación de la solicitud devuelve `400 VALIDATION_ERROR`. Algunas operaciones devuelven errores HTTP con `detail`.

## Paginación

Las colecciones paginadas reciben `page` desde 1 y `pageSize` de 1 a 100. Devuelven `items`, `page`, `pageSize`, `total`, `totalPages` y `hasNext`. Un resultado vacío tiene `totalPages: 1` y `hasNext: false`. Una página posterior a la última devuelve `items: []`.

| Colección | Filtro | Paginación recomendada |
| --- | --- | --- |
| `/clubs` | `name` | `?page=1&pageSize=20` |
| `/friendly-matches` | `creatorName` | `?page=1&pageSize=20` |
| `/players` | `search` | `?page=1&pageSize=9` |
| `/leagues` | `name` | `?page=1&pageSize=20` |

En `/players` y `/leagues`, enviar `pageSize` selecciona el contrato paginado común. Por compatibilidad, `limit` mantiene el formato anterior con `limit` y `totalPages`. `/players` sin tamaño sigue usando el formato anterior. `/leagues` sin `page`, `pageSize` ni `limit` sigue devolviendo todos los resultados en `items`.

## Operaciones HTTP

El cuerpo indica el esquema JSON que se puede consultar en OpenAPI. La tabla enumera las respuestas de éxito. Para verificar la referencia con el backend local desde la raíz del repo, ejecutar:

```sh
curl -fsS http://localhost:8000/openapi.json | python3 docs/check_api_reference.py
```

| Método | Ruta | Éxito | Cuerpo | Operación |
| --- | --- | --- | --- | --- |
| GET | `/health` | `200` | — | Estado del proceso. |
| GET | `/health/ready` | `200` | — | Disponibilidad de PostgreSQL y del esquema. |
| POST | `/auth/register` | `202` | `RegisterRequest` | Inicia el registro y envía el código de verificación. |
| POST | `/auth/verify-email` | `200` | `VerifyEmailRequest` | Confirma el correo y crea la cuenta. |
| POST | `/auth/resend-verification` | `200` | `ResendVerificationRequest` | Reenvía el código de una verificación pendiente. |
| POST | `/auth/login` | `200` | `LoginRequest` | Inicia sesión y establece la cookie. |
| GET | `/auth/me` | `200` | — | Identidad de la sesión. |
| POST | `/auth/logout` | `204` | — | Cierra la sesión. |
| POST | `/auth/change-password` | `204` | `ChangePasswordRequest` | Cambia la contraseña y cierra la sesión. |
| GET | `/clubs` | `200` | — | Lista otros clubes, con filtro por nombre. |
| GET | `/clubs/{club_id}` | `200` | — | Perfil, jugadores, estadísticas y posición del club. |
| GET | `/clubs/me` | `200` | — | Datos del club de la sesión. |
| PATCH | `/clubs/me` | `200` | `ClubUpdate` | Actualiza nombre, avatar y disponibilidad para amistosos. |
| GET | `/clubs/me/leagues` | `200` | — | Ligas en las que está inscripto el club. |
| GET | `/clubs/me/default-team` | `200` | — | Alineación predeterminada. |
| PUT | `/clubs/me/default-team` | `200` | `Lineup` | Reemplaza la formación, titulares, suplentes y sus comportamientos. |
| PATCH | `/clubs/me/dt` | `200` | `DtUpdate` | Actualiza activación y comportamiento del DT para futuros partidos. |
| GET | `/clubs/me/dt/behaviours` | `200` | — | Catálogo de comportamientos del DT. |
| POST | `/clubs/me/dt/behaviours` | `201` | `DtBehaviourCreate` | Crea un comportamiento para el DT. |
| GET | `/catalogs/formations` | `200` | — | Catálogo de formaciones. |
| GET | `/players` | `200` | — | Lista y busca jugadores propios. |
| GET | `/players/by-ids` | `200` | — | Lee jugadores propios por parámetros `ids` repetidos. |
| POST | `/players` | `201` | `PlayerCreate` | Crea un jugador con sus atributos PACSS. |
| PATCH | `/players/{player_id}/behaviour` | `200` | `PlayerBehaviourUpdate` | Asigna el comportamiento del jugador. |
| GET | `/behaviours` | `200` | — | Catálogo de comportamientos de jugadores. |
| GET | `/behaviours/{behaviour_id}` | `200` | — | Detalle de un comportamiento propio. |
| POST | `/behaviours` | `201` | `BehaviourCreate` | Crea un comportamiento de jugador. |
| DELETE | `/behaviours/{behaviour_id}` | `204` | — | Elimina un comportamiento que se puede retirar. |
| POST | `/behaviours/validate` | `200` | `BehaviourValidateRequest` | Valida un programa de jugador o DT. |
| GET | `/leagues` | `200` | — | Ligas disponibles, con filtro por nombre. |
| POST | `/leagues/public` | `201` | `CreateLeagueRequest` | Crea una liga pública. |
| POST | `/leagues/private` | `201` | `CreatePrivateLeagueRequest` | Crea una liga privada con contraseña. |
| GET | `/leagues/{id}/lobby` | `200` | — | Datos de la sala de espera e inscripciones. |
| POST | `/leagues/{id}/join` | `201` | `LeagueJoinRequest` | Inscribe al club con su alineación y el código si se requiere. |
| POST | `/leagues/{id}/leave` | `200` | — | Retira al club o cancela la liga si sale su creador. |
| POST | `/leagues/{id}/start` | `200` | — | Inicia la liga y genera sus rondas. |
| GET | `/leagues/{id}/fixture` | `200` | — | Rondas, horarios, resultados y próximo partido. |
| GET | `/leagues/{id}/ranking` | `200` | — | Tabla de posiciones de la liga. |
| GET | `/leagues/{id}/lineup` | `200` | — | Alineación propia en la liga, versión y permiso de edición. |
| PUT | `/leagues/{id}/lineup` | `200` | `LeagueLineupUpdate` | Guarda el plantel de liga con `expectedVersion`. |
| GET | `/friendly-matches` | `200` | — | Amistosos disponibles por club creador. |
| GET | `/friendly-matches/me` | `200` | — | Amistosos propios. |
| POST | `/friendly-matches` | `201` | `CreateFriendlyMatchRequest` | Crea un amistoso con `startDateTime` en ISO 8601. |
| POST | `/friendly-matches/{match_id}/join` | `200` | — | Une al club al amistoso indicado en el path. |
| POST | `/friendly-matches/behaviour-test` | `201` | — | Crea un partido de prueba contra el bot. |
| GET | `/matches/{match_id}` | `200` | — | Snapshot de un amistoso, partido de liga o prueba. |
| POST | `/matches/{match_id}/live-requests` | `200` | `LiveRequestCreate` | Encola un cambio con `playerId` y `behaviourId`. Devuelve `queued` y `requestId`. |
| POST | `/matches/{match_id}/dt` | `200` | `MatchDtUpdate` | Cambia `dtActive` para el partido. |
| PUT | `/matches/{match_id}/planned-substitution` | `200` | `PlannedSubstitutionRequest` | Planifica una sustitución con `outPlayerId`, `inPlayerId` y `commandId`. |
| POST | `/matches/{match_id}/substitutions` | `202` | `SubstitutionRequest` | Solicita un cambio durante una pausa e incluye `pauseId`. |

## WebSocket de partidos

`WS /matches/{match_id}/stream` transmite el mismo formato de snapshot que `GET /matches/{match_id}`. Ambos accesos requieren una sesión de un club participante. El stream valida el `Origin`, envía cambios de secuencia y vuelve a comprobar la sesión durante la conexión. El cliente puede pedir el snapshot por HTTP al conectar o reconectar. El estado del partido, el marcador y los cambios confirmados se obtienen del snapshot.

## Compatibilidad durante la migración

Las rutas anteriores de esta tabla siguen respondiendo directamente con su método, cuerpo, estado y formato anteriores. OpenAPI muestra las rutas canónicas.

| Ruta anterior | Ruta canónica |
| --- | --- |
| `/club` y sus rutas hijas | `/clubs` y sus rutas hijas |
| `/team/default` | `/clubs/me/default-team` |
| `/dt` y `/dt/behaviours` | `/clubs/me/dt` y `/clubs/me/dt/behaviours` |
| `POST /friendly-matches/join` con `idPartido` | `POST /friendly-matches/{match_id}/join` |
| `GET /friendly-matches/{match_id}` con el resumen de marcador | `GET /matches/{match_id}` con el snapshot |
| `POST /friendly-matches/{match_id}/dt` con `dt_active` | `POST /matches/{match_id}/dt` con `dtActive` |
| `POST /matches/{match_id}/live_request` con `player_id` y `behaviour_id` | `POST /matches/{match_id}/live-requests` con `playerId` y `behaviourId` |
