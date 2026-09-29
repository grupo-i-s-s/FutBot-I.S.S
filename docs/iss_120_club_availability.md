# ISS-120 — Consultar mi club y cambiar disponibilidad

Implementación en `feature/club-availability`, basada en la referencia local
`origin/feature/auth` (`eae2399`). No requiere cambios de esquema: reutiliza `Club`
y la migración `backend/migrations/001_auth.sql` de Autenticación.

## Contrato implementado

Ambas rutas usan la cookie `FutBotSession` que genera `POST /auth/login`.
La identidad proviene de `CurrentIdentity`; no se recibe el dueño desde el cliente.

### GET /club/me

Devuelve `200` con los datos públicos del club del usuario autenticado:

```json
{
  "id": 1,
  "name": "Mi club",
  "avatar": "valor-actual-del-registro",
  "friendlyAvailable": false
}
```

### PATCH /club/me

Recibe únicamente el campo obligatorio `friendlyAvailable`, como booleano JSON:

```json
{"friendlyAvailable": true}
```

Devuelve `200` con el mismo formato de Club actualizado. Un GET posterior recupera
el estado persistido. Solo cambia disponibilidad; conserva nombre y avatar.

Las escrituras usan el control existente de `feature/auth`: origen incluido en
`AUTH_ALLOWED_ORIGINS` y encabezado `X-Futbot-Request: 1`. Desde frontend:

```javascript
const response = await fetch('/api/club/me', {
  method: 'PATCH',
  credentials: 'same-origin',
  headers: {
    'Content-Type': 'application/json',
    'X-Futbot-Request': '1',
  },
  body: JSON.stringify({ friendlyAvailable: true }),
})
// El navegador agrega Origin. Comprobar response.ok antes de confirmar el cambio.
```

Errores con el formato compartido `{error:{code,message,fields}}`:

| HTTP | Código | Caso |
| --- | --- | --- |
| 400 | VALIDATION_ERROR | Campo ausente, null, texto, número o campos adicionales. |
| 401 | SESSION_INVALID | Cookie ausente, desconocida, inválida o vencida. |
| 403 | CSRF_INVALID | Escritura sin el encabezado requerido o con origen no permitido. |
| 409 | ACCOUNT_INCOMPLETE | Usuario autenticado sin club asociado. |

## Alcance respecto de Jira y del acuerdo del equipo

- Consulta y actualización de disponibilidad: implementadas.
- Permisos, aislamiento por usuario y persistencia: cubiertos por pruebas.
- El campo sigue llamándose `avatar`, igual que en Autenticación. El avatar se lee
  sin interpretarlo; catálogo, `avatarId` y edición esperan la definición del equipo.
- El PATCH todavía rechaza `name`: su edición corresponde a ISS-111.
- Desactivar disponibilidad solo modifica el club. No cancela ni modifica partidos.
  Lucas debe consultar este valor al crear/unirse a nuevos amistosos; el bloqueo de
  esas operaciones se verificará cuando exista su integración.

Por esos ajustes de alcance, la descripción anterior de Jira que menciona `avatarId`
y los tres tipos de edición no describe exactamente esta entrega. Jira no fue editado.

## Código y verificación

- `app/controller/club_controller.py`: rutas y uso de identidad autenticada.
- `app/schemas/club_schemas.py`: formato público y booleano estricto, sin campos extra.
- `app/services/club_service.py`: reglas, commit y rollback ante fallos.
- `app/repository/club_repository.py`: lectura reutilizada de auth y cambio de campo.
- `tests/test_club_availability.py`: 28 casos nuevos sobre una base SQLite aislada,
  con autenticación real por cookies y una sesión de base distinta por petición.

Desde la raíz, con el entorno Docker iniciado como indica el README principal:

```sh
docker compose exec backend python -m pytest -q
```

Resultado local: **34 pruebas aprobadas**, incluidas las existentes de errores de
Autenticación y salud sin base real. Se excluyó `test_readiness_checks_real_database`
porque Docker/PostgreSQL no están disponibles en el entorno de esta revisión.
La validación contra PostgreSQL y la prueba con la pantalla ISS-108 quedan pendientes.

Destino de revisión: `feature/auth`. Jira se actualiza manualmente por Gabi.
