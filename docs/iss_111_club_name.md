# ISS-111 — Editar el nombre del club (backend)

## Entrega

Rama `feature/club-name`, basada en `feature/club-availability` (`f94d558`, ISS-120).
No depende del frontend de ISS-108. Conserva el modelo `Club` y no requiere migración.

`PATCH /club/me` permite enviar `name`, `friendlyAvailable` o ambos. El club siempre
proviene de la sesión autenticada; no se admite un identificador de dueño del cliente.

```json
{"name": "Nuevo nombre"}
```

```json
{"name": "Nuevo nombre", "friendlyAvailable": true}
```

Devuelve `200` con `{id, name, avatar, friendlyAvailable}`. Un GET posterior recupera
lo guardado. Se conservan los campos omitidos; cambiar nombre no altera avatar ni
disponibilidad. El cliente de ISS-108 que manda solo `friendlyAvailable` sigue funcionando.

## Reglas y errores

- Se reutiliza `Name` del registro: quitar espacios exteriores y validar entre
  1 y 50 caracteres, después de esa normalización. Se conservan espacios internos.
- No se exige nombre único: el registro y el modelo actual tampoco lo exigen.
- Se rechazan `{}`, null explícito, nombre vacío o de espacios, tipos incorrectos,
  nombre demasiado largo, avatar, IDs y cualquier campo desconocido.
- `friendlyAvailable` sigue siendo booleano estricto: números y texto no se convierten.
- Se permite reenviar el mismo nombre; no se genera un conflicto por no cambiarlo.
- Si un campo es inválido, no se modifica ninguno. Ambos campos se guardan en
  una transacción; ante un fallo se hace rollback.
- Se mantienen cookie `FutBotSession`, origen permitido y `X-Futbot-Request: 1`.

Errores existentes: `400 VALIDATION_ERROR` con `fields`, `401 SESSION_INVALID`,
`403 CSRF_INVALID` y `409 ACCOUNT_INCOMPLETE`.

La validación está en el schema, el controller recibe la identidad, el servicio
coordina actualización/commit/rollback y el repositorio modifica el modelo.

## Verificación

Resultado local: **68 pruebas aprobadas, 1 excluida** (la comprobación de conexión
real a PostgreSQL, no disponible en este entorno). Los tests usan una base SQLite
aislada con sesión nueva por petición y autenticación por cookies.

Incluyen nombre solo y mixto, límites y Unicode, normalización, persistencia por
GET, conservación de avatar/disponibilidad/club ajeno, compatibilidad con ISS-120,
errores de campos/permisos/CSRF y rollback real tras flush y fallo de commit.

Con el entorno completo levantado según README, ejecutar:

```sh
docker compose exec backend python -m pytest -q
```

## Avance para Jira (actualización manual por Gabi)

No se modificó Jira. El ticket está en curso según lo informado por Gabi.

Comentario sugerido:

> Implementado en feature/club-name. PATCH /club/me admite name y/o friendlyAvailable,
> valida el nombre con las mismas reglas del registro y conserva los campos omitidos.
> Mantiene autenticación, CSRF, aislamiento entre clubes y rollback ante fallos.
> 68 pruebas locales aprobadas con SQLite; pendiente validación con PostgreSQL
> y revisión/integración. Depende de ISS-120 y será consumido por ISS-112.

- [x] Backend implementado y probado localmente.
- [x] Contrato y documentación actualizados.
- [ ] Publicación/revisión de la rama.
- [ ] Integración con la pantalla de ISS-112.
- [ ] Prueba completa con PostgreSQL.

Cuando ISS-120 esté integrada, revisar esta rama contra `feature/auth` actualizada;
mientras tanto la comparación de solo ISS-111 es contra `feature/club-availability`.
La edición de avatar sigue pendiente de definición del equipo.
