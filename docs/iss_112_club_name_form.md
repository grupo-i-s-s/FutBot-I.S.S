# ISS-112 — Formulario para editar el nombre del club

## Ramas y dependencias

| Ticket | Rama | Base y dependencia |
| --- | --- | --- |
| ISS-111, backend | `feature/club-name` | `feature/club-availability` (ISS-120). |
| ISS-112, frontend | `feature/club-name-form` | `feature/my-club` (ISS-108), con merge local de `feature/club-name`. |

ISS-111 conserva su rama independiente del frontend. ISS-112 combina las dos
dependencias para poder probar la edición desde la pantalla; las ramas anteriores
no fueron modificadas. La rama actual permite ver el avance completo de Clubes.

Para publicar/revisar, primero resolver las dependencias ISS-120/ISS-108 e ISS-111.
Si se abre una PR de ISS-112 contra `feature/my-club` antes de integrar ISS-111,
el diff incluirá también su backend: indicar esa dependencia en la descripción.
Una vez que las dependencias estén integradas, comparar contra `feature/auth`
actualizada y comprobar que el diff final solo contenga lo pendiente.

## Qué hace la pantalla

1. En `/club`, «Cambiar nombre» abre un formulario con el nombre actual y enfoca el campo.
2. Permite escribir, cancelar sin enviar una petición o guardar con `PATCH /club/me`.
3. Valida el nombre después de quitar espacios exteriores: obligatorio, 1–50 caracteres.
   Cuenta caracteres Unicode para coincidir con Python. No agrega reglas de unicidad.
4. Envía únicamente `{"name": "Nuevo nombre"}`, con cookie y protección CSRF existentes.
5. Mientras guarda, deshabilita el campo, guardar, cancelar y disponibilidad.
6. Solo cambia la cabecera con la respuesta del servidor, muestra «Nombre guardado»
   y devuelve el foco al botón de edición. Recargar consulta el valor guardado.
7. Ante error conserva el borrador y el último nombre confirmado. Asocia errores
   `fields.name` al campo y permite reintentar o volver a consultar el estado real.
   Esa consulta mantiene el editor y el borrador abiertos, incluso si también falla
   el GET; solo una sesión inválida o cuenta sin club retira los datos privados.
8. Ante sesión vencida retira los datos privados y muestra el estado de ingreso
   ya usado por ISS-108. No implementa otra pantalla de autenticación.

Cancelar restaura el valor confirmado al reabrir el formulario. Guardar un nombre
igual al actual (después de normalizarlo) está deshabilitado. Los errores de red
no se presentan como prueba de que el servidor haya rechazado el cambio: puede
haber guardado antes de perderse la respuesta, por eso se permite volver a consultar.

## Organización del código

- `features/clubs/components/ClubNameForm.jsx`: edición, validación, foco y mensajes.
- `features/clubs/api.js`: operación `updateClubName`, sin enviar otros campos.
- `features/clubs/hooks/useMyClub.js`: actualización del club confirmado y bloqueo
  compartido entre cambios de nombre/disponibilidad. Los mensajes de ambas
  operaciones se distinguen para no mostrar «Disponibilidad guardada» al renombrar.
- `features/clubs/MyClubPage.jsx`: incorpora el formulario a la tarjeta existente.
- `features/clubs/ClubNameForm.test.js`: pruebas de navegador de este flujo.

Se usan Tailwind y el Button existente. No se agregaron dependencias ni se cambió
el avatar, la creación inicial del club, los jugadores o los módulos de otras personas.

## Verificación

Backend ISS-111: **68 pruebas aprobadas con SQLite**, sin conexión a PostgreSQL.
La prueba de disponibilidad de PostgreSQL quedó excluida por falta de ese servicio.

Frontend: **28 pruebas de Chromium aprobadas** con respuestas HTTP simuladas
(15 existentes de ISS-108 y 13 de ISS-112). Se cubren guardado, normalización,
límites, Unicode, cancelar, no-op, errores de campo y red, recuperación conservando
el borrador, sesión vencida, bloqueo de escrituras y pantalla chica.
**Compilación de producción correcta**. Capturas de escritorio y pantalla de
320 px revisadas; los artefactos locales quedan en `frontend/test-results/` (sin versionar).

Con dependencias y Chromium instalados, desde `frontend/`:

```sh
npm test
npm run build
```

Para la prueba real, levantar el entorno según el README y usar una sesión de Auth:
abrir `/club`, cambiar el nombre, guardar, recargar, verificar disponibilidad y
probar también nombre vacío y cancelación. Repetir con otra cuenta para comprobar
que su nombre no cambia. No usar los fixtures simulados como evidencia de PostgreSQL.

## Avance para Jira

No se modificó Jira. Gabi informó ambos tickets En curso; los textos siguientes
están listos para copiar manualmente cuando comparta el avance.

**ISS-111:**

> Backend implementado en feature/club-name. PATCH /club/me admite name y/o
> friendlyAvailable, conserva campos omitidos y valida el nombre como el registro.
> Mantiene aislamiento por usuario, sesión por cookie, CSRF y rollback.
> 68 pruebas locales aprobadas sobre SQLite. Pendiente revisión/integración y
> validación con PostgreSQL. Dependencia: ISS-120.

**ISS-112:**

> Formulario Cambiar nombre implementado en feature/club-name-form, sobre la
> pantalla de ISS-108 y el backend de ISS-111. Incluye validación, guardar/cancelar,
> mensajes de éxito/error, conservación del borrador y bloqueo de escrituras
> simultáneas. Compilación correcta y 28 pruebas de navegador aprobadas con API
> simulada. Pendiente revisión/integración y prueba del recorrido con Auth y
> PostgreSQL. El avatar sigue pendiente de definición y queda fuera de estos tickets.

Conservar ambos En curso hasta compartir la entrega; cuando haya PR, pasarlos
al estado de revisión que use el equipo. No confundir código terminado localmente
con integración completa. Etiquetas: `clubes` + `backend` para ISS-111 y `clubes`
+ `frontend` para ISS-112, conservando etiquetas de requerimientos ya existentes.

## Checklist para actualizar el avance

- [x] Backend de edición de nombre implementado y probado.
- [x] Formulario integrado con el contrato de PATCH.
- [x] Compatibilidad con disponibilidad y avatar conservado.
- [x] Documentación y comentarios sugeridos de Jira.
- [x] 28 pruebas de navegador, compilación y capturas revisadas.
- [x] Commits locales separados; frontend incluye las dependencias de ISS-108/111.
- [ ] Ramas publicadas y PR abiertas.
- [ ] Revisión e integración con las ramas del equipo.
- [ ] Flujo completo validado con PostgreSQL.
- [ ] Jira actualizado por Gabi.
