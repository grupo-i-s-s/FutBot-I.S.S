# title: FutBot API
# version: 0.4.0
# description: FutBot API 


| Método | Endpoint | Resumen / Descripción | Parámetros | Request Body (Campos y Reglas) | Códigos y Respuestas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/auth/register` | Registrar usuario (Sin auth) | — | **JSON (Requerido):**<br>• `name` (str) req<br>• `username` (str) req<br>• `email` (email) req<br>• `password` (password) req | • `201`: Usuario registrado<br>• `400`: Datos inválidos o duplicados |
| **POST** | `/auth/login` | Iniciar sesión (Sin auth) | — | **JSON (Requerido):**<br>• `email` (email) req<br>• `password` (password) req | • `200`: Sesión iniciada<br>• `401`: Credenciales inválidas |
| **POST** | `/auth/change-password` | Cambiar contraseña | — | **JSON (Requerido):**<br>• `oldPassword` (password) req<br>• `newPassword` (password) req | • `200`: Contraseña actualizada<br>• `400`: Datos incompletos o contraseña inválida |
| **GET** | `/club/me` | Obtener mi club | — | — | • `200`: Club |
| **PATCH** | `/club/me` | Modificar mi club | — | **JSON (Requerido):**<br>• `name` (str)<br>• `avatar` (str)<br>• `friendlyAvailable` (bool) | • `200`: Club actualizado |
| **GET** | `/clubs/{clubId}` | Consultar perfil de club rival | • `clubId` (path, int) req | — | • `200`: Información pública del rival, estadísticas y plantilla de jugadores<br>• `404`: Club rival no encontrado |
| **GET** | `/players` | Listar jugadores | — | — | • `200`: Jugadores |
| **POST** | `/players` | Crear jugador | — | **JSON (Requerido):**<br>*Regla: Cada PACSS va de 20 a 100 y la suma debe ser 300.*<br>• `name` (str) req<br>• `power` (int, 20-100) req<br>• `agility` (int, 20-100) req<br>• `control` (int, 20-100) req<br>• `speed` (int, 20-100) req<br>• `strength` (int, 20-100) req | • `201`: Jugador creado<br>• `400`: PACSS inválido o sumatoria distinta de 300 |
| **DELETE** | `/players/{playerId}` | Eliminar jugador | • `playerId` (path, int) req | — | • `204`: Jugador eliminado<br>• `403`: El jugador no puede eliminarse (menos de 7 jugadores o partido/liga en curso) |
| **GET** | `/behaviours` | Listar comportamientos | — | — | • `200`: Comportamientos |
| **POST** | `/behaviours` | Crear comportamiento | — | **JSON (Requerido):**<br>• `name` (str) req<br>• `code` (str) req | • `201`: Comportamiento creado<br>• `403`: El club tiene un partido en curso |
| **PATCH** | `/behaviours/{behaviourId}` | Editar comportamiento | • `behaviourId` (path, int) req | **JSON (Requerido):**<br>• `name` (str) req<br>• `code` (str) req | • `200`: Comportamiento actualizado<br>• `403`: No se puede editar ahora |
| **DELETE** | `/behaviours/{behaviourId}` | Eliminar comportamiento | • `behaviourId` (path, int) req | — | • `204`: Comportamiento eliminado<br>• `403`: No se puede eliminar ahora |
| **GET** | `/team/default` | Obtener equipo default | — | — | • `200`: Equipo default |
| **PUT** | `/team/default` | Configurar equipo default | — | **JSON (Requerido):**<br>• `playerIds` (array[int], min: 6, max: 6, únicos) req<br>• `formation` (str) req | • `200`: Equipo actualizado<br>• `400`: El equipo debe tener 6 jugadores válidos |
| **GET** | `/leagues` | Listar ligas disponibles | • `name` (query, str) | — | • `200`: Ligas |
| **POST** | `/leagues` | Crear liga | — | **JSON (Requerido):**<br>• `name` (str) req<br>• `type` (enum: PUBLIC, PRIVATE) req<br>• `minTeams` (int, min: 3) req<br>• `maxTeams` (int, min: 3) req<br>• `startDateTime` (date-time) req<br>• `roundInterval` (enum: CONTINUOUS, DAILY, WEEKLY) req<br>• `accessCode` (str) | • `201`: Liga creada<br>• `400`: Configuración inválida |
| **GET** | `/leagues/{leagueId}` | Obtener detalle de liga | • `leagueId` (path, int) req | — | • `200`: Liga, fixture y tabla de posiciones |
| **POST** | `/leagues/{leagueId}/join` | Unirse a una liga<br>*(Usa y congela los 6 jugadores del equipo default)* | • `leagueId` (path, int) req | **JSON (Opcional):**<br>• `accessCode` (str) | • `201`: Club inscripto<br>• `409`: Liga llena, código inválido o club ya inscripto |
| **POST** | `/leagues/{leagueId}/leave` | Abandonar liga | • `leagueId` (path, int) req | — | • `204`: Club removido<br>• `409`: La liga ya inició |
| **POST** | `/leagues/{leagueId}/start` | Iniciar liga | • `leagueId` (path, int) req | — | • `200`: Liga iniciada y fixture generado<br>• `409`: No se puede iniciar la liga |
| **POST** | `/leagues/{leagueId}/cancel` | Cancelar liga | • `leagueId` (path, int) req | — | • `204`: Liga cancelada<br>• `409`: No se puede cancelar la liga |
| **GET** | `/matches/{matchId}` | Consultar partido<br>*(Devuelve estado actual si está en curso)* | • `matchId` (path, int) req | — | • `200`: Partido |
| **PUT** | `/matches/{matchId}/lineup` | Configurar alineación | • `matchId` (path, int) req | **JSON (Requerido):**<br>• `starters` (array[int], len: 3) req<br>• `substitutes` (array[int], len: 3) req<br>• `formation` (str) req<br>• `behaviours` (map/dict[str, int]) req | • `200`: Alineación guardada<br>• `400`: Alineación inválida |
| **POST** | `/matches/{matchId}/substitution` | Planificar o realizar cambio | • `matchId` (path, int) req | **JSON (Requerido):**<br>• `playerOutId` (int) req<br>• `playerInId` (int) req<br>• `mode` (enum: PLAN, APPLY) req | • `200`: Cambio aceptado<br>• `409`: Cambio no permitido |
| **DELETE** | `/matches/{matchId}/substitution` | Anular cambio planificado | • `matchId` (path, int) req | — | • `204`: Cambio anulado |
| **PATCH** | `/matches/{matchId}/players/{playerId}/behaviour` | Cambiar comportamiento de un jugador | • `matchId` (path, int) req<br>• `playerId` (path, int) req | **JSON (Requerido):**<br>• `behaviourId` (int) req | • `204`: Comportamiento cambiado |
| **GET** | `/friendly-matches` | Listar amistosos disponibles | — | — | • `200`: Amistosos |
| **POST** | `/friendly-matches` | Crear amistoso | — | **JSON (Requerido):**<br>• `startDateTime` (date-time) req | • `201`: Amistoso creado |
| **POST** | `/friendly-matches/{matchId}/join` | Unirse a un amistoso | • `matchId` (path, int) req | — | • `200`: Club unido al partido<br>• `409`: Partido completo |
| **GET** | `/leaderboard` | Consultar ranking global | — | — | • `200`: Ranking |


