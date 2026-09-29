# ISS-108 — Mi club: implementación y machete para Jira

## Rama y dependencia

- Rama: `feature/my-club`.
- Base: `feature/club-availability`, commit `f94d558`, que a su vez deriva de
  `feature/auth`. Incluye el backend de ISS-120 para poder avanzar antes de su merge.
- PR del backend: https://github.com/grupo-i-s-s/FutBot-I.S.S/pull/1.
- Mientras esa PR esté abierta, una PR del frontend puede comparar contra
  `feature/club-availability` para mostrar solo ISS-108. Después de integrar el
  backend, actualizar la base de revisión a `feature/auth` y revisar el diff.
  Si se integra con squash/rebase, puede hacer falta rebasar esta rama para no
  arrastrar el commit original de ISS-120.
- Entrega preparada para revisión. Antes de integrarla, revisar los pendientes
  de autenticación, navegación, avatar y PostgreSQL detallados más abajo.

## Qué está implementado

- Pantalla `/club`, accesible desde «Ir a Mi club» en `/`.
- Consulta del club autenticado: muestra el nombre real y `friendlyAvailable`.
- Interruptor accesible con teclado para activar/desactivar disponibilidad.
- Solo confirma el cambio cuando responde el backend y usa el objeto devuelto.
- Deshabilita el interruptor durante el guardado y evita solicitudes duplicadas.
- Ante un rechazo conserva el último valor confirmado y permite reintentar.
- Ante una falla de red no asegura que el servidor haya rechazado la escritura:
  permite volver a consultar para recuperar el estado real.
- Distingue carga, fallo de lectura, sesión ausente/vencida y cuenta sin club.
- Cancela solicitudes al desmontar y limita a 10 segundos el tiempo de espera.
- Explica que disponibilidad solo afecta nuevas participaciones y no cancela
  compromisos aceptados ni modifica partidos en curso.
- Diseño adaptable, con Tailwind y el componente Button existente, según README.

El frontend usa rutas relativas `/api/club/me`. La autenticación viaja por cookie;
no almacena ni lee tokens. PATCH envía `X-Futbot-Request: 1` y exactamente
`{"friendlyAvailable": true}` o `{"friendlyAvailable": false}`. El origen lo
agrega el navegador; debe estar permitido por `AUTH_ALLOWED_ORIGINS`.

## Archivos y responsabilidades

| Archivo dentro de frontend | Responsabilidad |
| --- | --- |
| `src/api/http.js` | Proxy, cookies, encabezados, errores, cancelación y timeout. |
| `src/features/clubs/api.js` | GET/PATCH de Clubes y validación del formato recibido. |
| `src/features/clubs/hooks/useMyClub.js` | Estados de carga, guardado, errores y reintentos. |
| `src/features/clubs/MyClubPage.jsx` | Vista y control de disponibilidad. |
| `src/features/clubs/components/ClubNavigation.jsx` | Accesos configurables a otros módulos. |
| `src/main.jsx` | Montaje provisional de `/club`, hasta integrar el router compartido. |
| `src/features/clubs/MyClubPage.test.js` | Pruebas de comportamiento en Chromium. |

## Integración que falta

1. **Autenticación:** integrar esta página en el router/layout final y navegar a ella
   después del login. La rama base no trae pantallas de login o registro.
   No se implementa otra autenticación dentro de Clubes.
2. **Navegación:** pasar las rutas reales a `MyClubPage` mediante `destinations`.
   Claves: `players`, `team`, `behaviours`, `leagues`, `friendlyMatches`.
   Pasar `loginHref` para ofrecer el acceso a la pantalla de ingreso ante un 401.
   Las entradas sin ruta se muestran como «Próximamente», sin enlaces ficticios.
3. **Avatar:** hay un escudo provisional accesible. El campo `avatar` se recibe
   pero no se interpreta como URL, ID de catálogo u otro formato hasta la decisión
   del equipo. Mostrar el avatar real y editarlo quedan pendientes de esa definición.
4. **Lucas:** su backend debe consultar disponibilidad al crear/unirse a amistosos.
   Un mensaje en Mi club no aplica por sí solo esa regla en Amistosos.
5. **Validación integrada:** comprobar login real → Mi club → cambiar disponibilidad
   → recargar, sobre PostgreSQL y con el origen permitido de la aplicación.

La edición posterior del nombre corresponde a ISS-111; esta pantalla podrá
incorporar su acceso cuando exista. La edición del avatar sigue pendiente del
acuerdo del equipo. El registro y la creación inicial del club permanecen en Auth.

## Qué actualizar manualmente en Jira

No se hicieron cambios en Jira. Los siguientes son textos sugeridos, basados en
el alcance trabajado y el contrato implementado; no son una nueva lectura del
estado actual del tablero. Conservar criterios y etiquetas existentes que sigan
vigentes. Los pendientes no se consideran cumplidos por mostrarlos en la pantalla.

### ISS-108

- **Estado:** En progreso. No marcar Terminado mientras falten las integraciones
  exigidas por sus criterios de aceptación.
- **Responsable:** Gabi.
- **Épica:** Clubes.
- **Etiquetas sugeridas:** `clubes`, `frontend`; conservar `req-11`, `req-13`
  si ya están vinculadas al ticket. Usar la misma escritura que el tablero para
  no duplicar etiquetas equivalentes.
- **Dependencia:** ISS-120 provee GET/PATCH. Vincularlo como dependencia de
  integración; es posible avanzar en esta rama sin esperar el merge.
- **Rama:** `feature/my-club`.

**Descripción propuesta:**

> Como usuario autenticado quiero consultar mi club y cambiar su disponibilidad
> para nuevas participaciones en amistosos. La pantalla consulta GET /club/me y
> guarda únicamente friendlyAvailable con PATCH /club/me, usando la cookie de
> Autenticación y la protección de escritura existente. Muestra el nombre y la
> disponibilidad reales, informa carga y errores, permite reintentar y confirma
> el cambio solamente después de la respuesta del servidor. Ofrece accesos a los
> módulos a medida que estén integrados. El avatar se representa provisionalmente
> con un escudo hasta que el equipo acuerde su formato. La edición del nombre y
> del avatar se resuelve en sus tickets específicos.

**Criterios para revisar con el equipo:**

- Muestra nombre y disponibilidad obtenidos del club autenticado.
- Cambia solo friendlyAvailable, sin enviar nombre, avatar ni identidad del dueño.
- Confirma el valor devuelto por el servidor; tras recargar recupera el persistido.
- Evita doble envío; ante error mantiene el último valor confirmado y permite
  reintentar o volver a consultar el estado actual.
- Distingue carga, error de conexión, sesión inválida y cuenta sin club.
- Explica el efecto sobre nuevas participaciones y compromisos existentes.
- Funciona en pantalla angosta y con teclado.
- Permite navegar a los módulos y al login cuando sus rutas estén integradas.
  Este criterio sigue pendiente en el producto, aunque se prueba con rutas de ejemplo.
- El avatar real queda pendiente de definición; acordar explícitamente si se
  difiere ese criterio, sin marcarlo cumplido por el escudo provisional.

**Comentario de avance para pegar:**

> Implementada la pantalla Mi club en feature/my-club, basada en la rama de
> ISS-120. Incluye consulta, actualización de disponibilidad, carga, manejo de
> errores, reintentos y adaptación a pantalla chica. El guardado usa sesión por
> cookie y protección CSRF. Compilación correcta y 15 pruebas de navegador
> aprobadas con respuestas de API simuladas. Quedan pendientes integrar el login/router y las
> rutas de los demás módulos, definir el avatar y validar el flujo completo con
> PostgreSQL. La navegación pendiente figura como Próximamente. No se da por
> cerrado el ticket hasta verificar los criterios de integración.

### ISS-120

- **Estado sugerido:** En revisión, si existe ese estado en el flujo del equipo;
  de lo contrario mantener En progreso y registrar que hay una PR abierta.
- **Etiquetas:** `clubes`, `backend`, conservando las etiquetas de requerimientos.
- Adjuntar/enlazar la PR #1 y relacionar ISS-108 como consumidor de la API.
- Mantener como pendiente la validación con PostgreSQL y la integración con
  Amistosos; la PR no implementa el bloqueo de esas operaciones de Lucas.
- Si la descripción todavía menciona editar nombre/avatar dentro de este PATCH,
  corregirla para describir esta entrega: solo friendlyAvailable. El nombre se
  implementa en ISS-111 y el avatar espera definición.

**Comentario para pegar:**

> Backend de consulta y disponibilidad implementado en la PR #1 hacia feature/auth.
> GET /club/me devuelve el club autenticado y PATCH /club/me modifica únicamente
> friendlyAvailable. Se está integrando su consumo desde ISS-108. Pendiente revisión,
> validación con PostgreSQL y coordinación con Lucas para que crear/unirse a
> amistosos respete la disponibilidad. Nombre y avatar no se editan en esta entrega.

## Verificación y seguimiento

Las pruebas de frontend usan respuestas de API simuladas y rutas de navegación
exclusivas de prueba. No demuestran por sí solas persistencia real ni que los
módulos de otros integrantes ya estén disponibles.

Resultado local: **15 pruebas de Chromium aprobadas**, compilación de producción
correcta y capturas revisadas en escritorio y pantalla de 320 px. Cubren carga,
guardado y recarga sobre el servidor simulado, cookie/encabezado/body, errores de
lectura y escritura, red, timeout, respuesta inválida, 401, cuenta incompleta,
teclado y navegación configurada. Se agregó `@playwright/test` como dependencia
de desarrollo con versión exacta y lockfile actualizado.

Desde `frontend/`: `npm ci`, `npx playwright install chromium`, `npm test` y
`npm run build`. Ver alternativas con Docker en el README del frontend.

- [x] Implementación de la pantalla y conexión al contrato de ISS-120.
- [x] Rama `feature/my-club` separada de la PR del backend.
- [x] 15 pruebas de navegador aprobadas y capturas de escritorio/móvil revisadas.
- [x] Compilación de producción aprobada.
- [ ] Revisión e integración de la PR de ISS-120.
- [ ] Login/router integrado.
- [ ] Rutas reales de los cinco módulos integradas.
- [ ] Avatar definido e integrado o diferimiento acordado en Jira.
- [ ] Flujo real probado con PostgreSQL.
- [ ] Commit/PR de ISS-108 preparados para revisión.
- [ ] Jira actualizado por Gabi.
