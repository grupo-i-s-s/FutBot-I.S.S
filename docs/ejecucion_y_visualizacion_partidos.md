# Ejecución y visualización de amistosos

**Estado:** propuesta de contrato para implementar S2-19 a S2-23. No describe una funcionalidad ya implementada.

## Alcance y punto de partida

Un amistoso con dos clubes debe comenzar, ejecutar los comportamientos fijados, avanzar hasta un resultado y poder observarse sin refrescar la página. El servidor decide el estado del juego; el navegador sólo lo presenta. Quedan fuera de este ciclo las pausas, sustituciones, cambios de comportamiento durante el partido y partidos de liga.

Hoy `backend/app/controller/matches_controller.py` sólo expone `POST /partidos/unirse`, `backend/app/services/matches_service.py` asigna el visitante, `backend/app/models/matches_model.py` guarda participantes y fecha, y `backend/primitives/primitives.py` contiene `run_to` y `kick`. No hay todavía motor, persistencia de estado/resultado, `GET /matches/{matchId}`, WebSocket ni pantalla de observación. La pantalla `frontend/src/features/friendly-matches/Matches.jsx` lista datos fijos. 

## Flujo propuesto

1. Al llegar `startDateTime`, un único proceso reclama el amistoso mediante una transición atómica. Si falta rival, queda `CANCELLED`; si están los dos clubes y las alineaciones son válidas, fija titulares/comportamientos y pasa a `RUNNING`. No depende de que haya espectadores conectados. La programación del trabajo y el manejo de reinicios deben definirse antes de implementarlo.
2. Un motor por partido avanza la física con paso fijo. Para arrancar, se propone `dt = 1/30 s` y publicar un estado cada tres pasos (10 snapshots/s). Estos son parámetros de implementación, no duración ni reglas deportivas aprobadas. El reloj del partido deriva de los pasos simulados, nunca del número de mensajes enviados.
3. En cada ciclo, el motor construye la observación de cada titular, invoca su comportamiento fijado, valida la acción y la transforma en primitivas de movimiento o patada. Pymunk integra cuerpos y colisiones; una capa de reglas detecta goles, reposiciona tras el gol y decide el final. Sólo el motor puede cambiar posiciones, marcador y reloj. Los errores del comportamiento siguen la política que se acuerde para S2-20 y no detienen el ciclo.
4. Cada snapshot que se envía debe guardarse **antes** de publicarse, con su `sequence`; `GET` lee ese mismo estado. Así una caída no hace retroceder a un observador después de reconectar. No se guarda cada paso físico. Una primera versión puede persistir a 10 Hz por partido; medir el costo si se agregan muchos partidos simultáneos y ajustar juntas las frecuencias de persistencia/publicación. La estrategia de reanudación debe evitar un segundo motor o un resultado distinto. La finalización es idempotente.
5. Desconectarse de la vista no detiene el partido. Al finalizar, `GET /matches/{matchId}` continúa entregando el resultado y un estado final apto para dibujar.

### Responsabilidades de backend

Respetar la convención del repositorio: controller → service → repository, conservando modelos y schemas. El controller HTTP/WS sólo valida acceso y transporta datos; el servicio coordina el ciclo, reglas y publicación; el repositorio hace las transiciones atómicas y guarda estados/resultados. Separar el motor de simulación de los controladores evita que una conexión WebSocket sea dueña del partido. El proceso que publica puede tener muchos observadores, pero sólo un escritor del estado.

## Contrato de lectura y WebSocket propuesto

- `GET /matches/{matchId}` devuelve un `match.snapshot` con el último estado disponible, incluidos `WAITING`, `RUNNING`, `FINISHED` y `CANCELLED`. Es la entrada, recuperación y consulta histórica. Los códigos HTTP de inexistencia y acceso prohibido deben ser claros.
- `GET /matches/{matchId}/stream` se negocia como WebSocket. Tras autenticar y autorizar, envía **inmediatamente** el snapshot vigente y después cada snapshot publicado o transición de estado. Es un canal de lectura: el navegador no envía posiciones, reloj, marcador ni comandos de juego.
- Ambos transportes usan exactamente el mismo schema versionado. La publicación usa snapshots completos, no deltas: con seis titulares y una pelota el contrato es pequeño y el cliente no necesita reconstruir movimientos perdidos.
- `sequence` es monotónico por partido, se conserva al reiniciar el backend y aumenta con cada snapshot publicado o transición. HTTP y WS entregan el mismo valor para un mismo estado. El cliente descarta una secuencia menor o igual a la última aplicada. `sentAt` sirve para diagnóstico, no para calcular el reloj oficial.
- Al recibir `FINISHED` o `CANCELLED`, el cliente conserva ese estado, cierra el canal y no intenta reconectar. Si aún no existe un estado geométrico (por ejemplo `WAITING`), `players` está vacío y `ball` es `null`.

Ejemplo ilustrativo de un mensaje completo (las magnitudes y el tiempo son valores de muestra):

```json
{
  "schemaVersion": 1,
  "type": "match.snapshot",
  "matchId": 42,
  "sequence": 51,
  "sentAt": "2026-10-01T21:00:05.000Z",
  "state": {
    "status": "RUNNING",
    "clockMs": 5100,
    "durationMs": 300000,
    "field": { "width": 100, "height": 60, "goalWidth": 12 },
    "teams": [
      { "id": 7, "name": "Local", "side": "LEFT", "score": 1, "color": "#2563eb" },
      { "id": 9, "name": "Visitante", "side": "RIGHT", "score": 0, "color": "#dc2626" }
    ],
    "players": [
      { "id": 101, "teamId": 7, "name": "Jugador 1", "x": 28.4, "y": 18.2, "radius": 1.4 },
      { "id": 102, "teamId": 7, "name": "Jugador 2", "x": 32.0, "y": 31.0, "radius": 1.4 },
      { "id": 103, "teamId": 7, "name": "Jugador 3", "x": 27.0, "y": 44.0, "radius": 1.4 },
      { "id": 201, "teamId": 9, "name": "Jugador 4", "x": 70.0, "y": 17.0, "radius": 1.4 },
      { "id": 202, "teamId": 9, "name": "Jugador 5", "x": 68.0, "y": 30.0, "radius": 1.4 },
      { "id": 203, "teamId": 9, "name": "Jugador 6", "x": 72.0, "y": 43.0, "radius": 1.4 }
    ],
    "ball": { "x": 50.3, "y": 29.8, "radius": 0.5 }
  }
}
```

`durationMs = 300000` **no fija** que el partido dure cinco minutos: el documento de alcance dice “duración de 5” sin unidad, y Sprint 2 aún debe acordar duración y ritmo. Antes de codificar, definir `durationMs`, relación entre tiempo simulado y real, dimensiones del campo, tamaños, arcos y reglas de gol. El contrato permite cambiar esos valores sin modificar el renderer.

### Seguridad y conexión

La sesión actual está en una cookie `HttpOnly` con `SameSite=Lax`. El endpoint WS debe leerla, comprobar sesión y acceso al partido **antes de aceptar** la conexión, y validar el encabezado `Origin` contra los orígenes permitidos. No usar el ID del partido como autorización ni pasar el token por query string. Rechazar el handshake sin sesión, con origen no permitido o sin permiso para observar; si la sesión expira durante una conexión larga, cerrarla al detectarlo. En Sprint 2, el acceso mínimo son los dos clubes participantes; ampliar a espectadores de liga requiere una regla explícita.

El frontend usa `/api` como ruta relativa. Para el WebSocket debe construir `ws:` o `wss:` desde `window.location` y conectar a `/api/matches/{matchId}/stream`. En desarrollo, el proxy de Vite existente necesita `ws: true` además del rewrite de `/api`; el proxy de despliegue también deberá aceptar el upgrade de WebSocket. El backend seguirá viendo `/matches/{matchId}/stream`.

### Reconexión y estado desactualizado

La vista carga primero `GET /matches/{matchId}` y abre el WebSocket. El primer mensaje WS vuelve a traer el estado vigente y se aplica sólo si su `sequence` es mayor. Si el canal se cierra durante `RUNNING`, la vista muestra “Reconectando”, deja de animar datos vencidos, vuelve a consultar por HTTP y reintenta con demora creciente y límite razonable; al reconectar, el servidor envía un snapshot completo. No se reproducen todos los pasos perdidos. Si se agotan los reintentos, ofrecer “Reintentar” y mantener visible el último marcador con indicación de que no está en vivo.

## Cómo dibuja el frontend

La pantalla propuesta `MatchPage` separa dos capas:

1. **HTML/React:** nombres de clubes, marcador, reloj, estado, mensajes de reconexión y resultado. Estos datos son texto real para accesibilidad y no dependen de leer píxeles del canvas.
2. **Canvas 2D:** cancha, líneas, arcos, seis jugadores y pelota. Para este tamaño de escena basta la API Canvas del navegador, sin agregar una biblioteca gráfica en el primer corte. La cancha se dibuja en el cliente a partir de `field`; no se transmite una imagen completa por WebSocket.

El sistema de coordenadas de juego es único: origen `(0, 0)` en la esquina superior izquierda, `x` hacia la derecha e `y` hacia abajo; el centro es `(width/2, height/2)`. `LEFT` ataca hacia `x = width` y `RIGHT` hacia `x = 0`. Las posiciones son centros de entidades en unidades lógicas del motor, no píxeles. Backend y frontend deben compartir esta convención; cualquier conversión necesaria por el eje de Pymunk se hace al serializar el estado.

Para un canvas visible de `viewWidth × viewHeight`, mantener la relación `field.width / field.height` sin deformar. Con `scale = min(viewWidth / field.width, viewHeight / field.height)`, usar `offsetX = (viewWidth - field.width × scale)/2` y `offsetY = (viewHeight - field.height × scale)/2`. Un punto de juego `(x, y)` se dibuja en `(offsetX + x × scale, offsetY + y × scale)`; el radio se multiplica por `scale`. El mismo cálculo ubica las líneas del área, el círculo central y las porterías. No girar la cancha según el usuario, para que ambos observadores vean el mismo partido.

En cada redimensionamiento, ajustar el tamaño interno del canvas con `devicePixelRatio` y volver a calcular la transformación. Dibujar en este orden: fondo y marcas estáticas, porterías, jugadores con color de equipo y un identificador corto legible, y pelota con contorno contrastante. Mantener un estado visual sencillo si todavía no hay imagen de jugador; los escudos de clubes pueden ir en el marcador HTML, sin usar imágenes de avatars como condición para el partido.

`requestAnimationFrame` controla el dibujo. Mantener los dos snapshots más recientes y un retraso visual de aproximadamente 100 ms; interpolar sólo `x`/`y` de jugadores y pelota entre esas dos muestras. Marcador, reloj y estado se toman directamente del último snapshot del servidor; nunca se predice un gol ni se interpola un cambio de estado. Si falta el siguiente snapshot, sostener la última posición por un intervalo corto y mostrar la conexión degradada, sin extrapolar indefinidamente. Cuando cambia el marcador, el partido termina o se reconecta, vaciar el búfer y dibujar el estado recibido para evitar deslizamientos artificiales. React puede guardar estado de UI a ritmo de mensajes; las coordenadas por frame viven en refs del canvas, sin forzar un render de React a 60 Hz.

Estructura sugerida al implementar (archivos **propuestos**, no existentes):

```text
frontend/src/features/friendly-matches/
  MatchPage.jsx                 # carga, estados y composición
  matchApi.js                   # GET y URL de WebSocket
  hooks/useMatchStream.js       # conexión, secuencia y reconexión
  components/MatchCanvas.jsx    # transformación y dibujo
  components/MatchScoreboard.jsx
```

## Verificación de la implementación

- El mismo snapshot produce posiciones visibles correctas en tamaños de pantalla distintos, sin deformar la cancha ni sacar pelota/jugadores del área de juego.
- Dos navegadores ven el mismo marcador y la misma secuencia de posiciones; cerrar ambos navegadores no detiene la simulación.
- Un observador que entra tarde recibe de inmediato el estado actual; tras cortar y restaurar la red, recupera el estado sin retroceder en `sequence` ni duplicar goles.
- Un partido sin rival se cancela una vez; uno completo inicia una vez; al terminar persiste el mismo marcador consultado por HTTP y no se publican nuevos pasos físicos.
- Una sesión ausente o un `Origin` ajeno no puede abrir el WS. La vista distingue carga, espera, juego, cancelación, final, desconexión y error de autorización.

## Decisiones pendientes antes de programar

1. Confirmar con los profes la duración y unidad de “5”, velocidad del reloj, tamaño lógico de cancha/arcos, reglas mínimas de colisión, gol y reinicio, y el nivel visual exigido.
2. Fijar el contrato de comportamientos de S2-05 (observación, acción, prioridad, límites y error). Los comportamientos predeterminados actuales son provisionales y no prueban todavía el motor.
3. Definir cómo se programa y recupera una ejecución tras reinicio del backend, y si Sprint 2 correrá una sola instancia o varias. Elegir con ello persistencia periódica y mecanismo de difusión.
4. Acordar si sólo participantes pueden observar amistosos y unificar `/partidos` actual con las rutas `/matches` y `/friendly-matches` propuestas antes de implementar los clientes.

## Referencias técnicas

- [FastAPI: WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Vite: proxy con WebSocket y comprobación de origen](https://vite.dev/config/server-options.html#server-proxy)
- [MDN: optimización de Canvas, escala de píxeles y requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)
