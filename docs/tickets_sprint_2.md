# Propuesta de tickets — Sprint 2

**Entrega:** lunes 05/10/2026 a las 23:59.  
**Estado:** borrador para revisar con el equipo y consultar a los profes. No son tickets cargados en Jira ni estimaciones definitivas.

## Alcance que se tomó para esta propuesta

Esta descomposición parte de los 16 requerimientos y las aclaraciones de la consigna de Sprint 2. Los documentos `alcance_proyecto.MD`, `casos_de_uso.md` y `api_endpoints.md` aportan contexto, pero cuando difieren de la consigna de esta entrega se prioriza esta última. Los IDs `S2-XX` son provisionales para poder conversar sobre los tickets; no representan claves reales de Jira.

El recorrido que debe quedar funcionando es: registrar dos usuarios y sus clubes, preparar jugadores y equipos con comportamientos predeterminados, crear y gestionar ligas **sin iniciarlas**, y crear un amistoso, unir el rival, jugarlo completo y observarlo en la interfaz. Cada club recibe seis jugadores iniciales. **El equipo del proyecto define los valores PACSS y asigna los comportamientos de esos jugadores**; no se solicita esa elección al usuario durante el registro.

Quedan fuera de esta propuesta: iniciar o cancelar ligas; editar perfiles de usuario; crear, editar o eliminar comportamientos; pausas, sustituciones y cambios de comportamiento durante un partido; rankings, fixture de ligas y juego de partidos de liga. Esos temas pueden evaluarse para Sprint 3.

## Cuenta, club y plantel

### S2-01 — Registrar usuario y configurar su club

**Descripción.** Dado un visitante, cuando completa los datos válidos de registro y confirma, el sistema crea su cuenta y el club con el que participará en ligas y amistosos.

**Notas técnicas.** La API preliminar propone `POST /auth/register`, pero solo documenta los campos de usuario; el alcance y el caso de uso de registro también exigen nombre y avatar del club. Acordar el contrato final antes de implementarlo. La contraseña se guarda de forma segura, nunca en texto plano. El formulario solicita repetirla para detectar errores de carga.

**Criterios de aceptación.**

- Se solicitan nombre, username, email, contraseña, confirmación de contraseña, nombre de club y avatar de la biblioteca disponible.
- Se rechazan campos obligatorios vacíos, contraseñas que no coinciden, email inválido y username o email ya registrados, con mensajes comprensibles.
- Una operación exitosa deja usuario y club asociados y persistidos, sin crear registros parciales si falla.
- El nuevo usuario puede luego iniciar sesión.

**Dependencias:** ninguna.

**Esfuerzo orientativo:** 7/10.

**Subtickets propuestos:**

- **S2-01a — Persistir cuenta y club (4/10).** Implementar la operación de registro, la unicidad de email y username, el almacenamiento seguro de la contraseña y la creación atómica del club con nombre y avatar. **Terminado cuando:** una solicitud válida crea ambos registros y una inválida no deja datos parciales.
- **S2-01b — Construir formulario de registro (3/10).** Crear la vista con todos los campos, confirmación de contraseña y mensajes de validación. **Terminado cuando:** un visitante puede registrarse desde la interfaz y entiende por qué se rechaza una carga inválida.

### S2-02 — Iniciar sesión y acceder a las funciones privadas

**Descripción.** Dado un usuario registrado, cuando ingresa su email y contraseña correctos, el sistema inicia su sesión y le permite acceder a las funciones de su club.

**Notas técnicas.** La API preliminar propone `POST /auth/login`. Definir el mecanismo de sesión o token y aplicarlo a los endpoints protegidos de este sprint.

**Criterios de aceptación.**

- Las credenciales correctas permiten ingresar y conservan la identidad del usuario en las solicitudes posteriores.
- Las credenciales incorrectas se rechazan sin revelar cuál de los dos datos falló.
- Un visitante sin sesión no puede crear jugadores, ligas o amistosos ni inscribirse en ellos.
- La interfaz muestra los errores de autenticación y permite volver a intentarlo.

**Dependencias:** S2-01.

**Esfuerzo orientativo:** 5/10.

### S2-03 — Proveer plantel inicial y consultar jugadores del club

**Descripción.** Dado un club recién creado, el usuario puede consultar los jugadores disponibles para configurar un equipo. El sistema le provee seis jugadores iniciales definidos por el equipo del proyecto.

**Notas técnicas.** La API preliminar propone `GET /players`. El equipo del proyecto elige y documenta los atributos PACSS y los comportamientos asignados a los seis jugadores iniciales. La creación del usuario y del club debe dejarlos disponibles sin obligarlo a crearlos manualmente.

**Criterios de aceptación.**

- El club dispone de exactamente seis jugadores iniciales y cada jugador pertenece exclusivamente a ese club.
- Cada jugador inicial tiene valores PACSS válidos (cada atributo entre 20 y 100; suma 300) y un comportamiento predeterminado disponible para ese club.
- El usuario ve nombre y atributos de sus jugadores, incluidos los que cree después.
- No puede consultar el plantel privado de otro club mediante la operación de “mis jugadores”.

**Dependencias:** S2-01, S2-05.

**Esfuerzo orientativo:** 4/10.

### S2-04 — Crear jugador del club

**Descripción.** Dado un usuario autenticado, cuando carga un nombre y distribuye los puntos PACSS válidamente, el sistema crea un jugador en su club y lo agrega al plantel visible.

**Notas técnicas.** La API preliminar propone `POST /players`: `name`, `power`, `agility`, `control`, `speed` y `strength`.

**Criterios de aceptación.**

- El nombre es obligatorio y cada uno de los cinco atributos es un entero entre 20 y 100.
- La suma de los cinco atributos es exactamente 300; los valores inválidos se rechazan tanto en interfaz como en servidor.
- El jugador creado queda asociado al club autenticado y aparece en el listado sin tener que iniciar otra sesión.
- Un fallo no crea un jugador incompleto.

**Dependencias:** S2-02, S2-03.

**Esfuerzo orientativo:** 5/10.

## Comportamientos y equipo

### S2-05 — Definir la API de comportamientos y tres comportamientos predeterminados

**Descripción.** Dado un usuario registrado, el sistema le ofrece al menos tres comportamientos predeterminados, escritos en Python y válidos según la API de comportamientos del proyecto.

**Notas técnicas.** Documentar el contrato de entrada, salida y acciones permitidas antes de codificar los tres ejemplos. La API preliminar de endpoints documenta la gestión de comportamientos, pero no especifica el contrato de ejecución de Python. Si los predeterminados son compartidos o se copian por usuario, el resultado observable debe ser el mismo: cada usuario tiene los tres disponibles.

**Criterios de aceptación.**

- Existen al menos tres comportamientos identificables y seleccionables por cada usuario registrado, incluido uno recién creado.
- Cada comportamiento respeta las reglas de la API de comportamientos acordada y puede ejecutarse con entradas válidas.
- Los comportamientos predeterminados permanecen disponibles entre sesiones.
- Se documenta qué hace cada uno para que el equipo pueda verificarlo durante un partido.

**Dependencias:** S2-01; acuerdo sobre la API de comportamientos.

**Esfuerzo orientativo:** 8/10.

**Subtickets propuestos:**

- **S2-05a — Acordar y documentar la API de comportamientos (3/10).** Definir entrada, salida, acciones permitidas y restricciones de ejecución. **Terminado cuando:** existe un contrato concreto que pueden usar quienes implementen los comportamientos y el motor.
- **S2-05b — Implementar y disponibilizar tres comportamientos predeterminados (3/10).** Escribir los tres comportamientos en Python y asociarlos a cada usuario nuevo y existente según el modelo elegido. **Terminado cuando:** cualquier usuario puede identificarlos y seleccionarlos.
- **S2-05c — Validar la ejecución de los comportamientos predeterminados (2/10).** Preparar ejemplos de entrada y verificar salida, acciones permitidas y errores. **Terminado cuando:** los tres se ejecutan conforme al contrato documentado.

### S2-06 — Listar comportamientos disponibles

**Descripción.** Dado un usuario autenticado, cuando abre la sección de comportamientos o configura su equipo, ve los comportamientos que puede seleccionar.

**Notas técnicas.** La API preliminar propone `GET /behaviours`. Definir los campos mínimos del listado, como identificador, nombre y descripción breve.

**Criterios de aceptación.**

- El listado incluye los tres comportamientos predeterminados del usuario.
- Cada entrada permite identificar el comportamiento y abrir su detalle.
- Los errores de carga se informan sin mostrar una lista engañosamente vacía.

**Dependencias:** S2-05.

**Esfuerzo orientativo:** 3/10.

### S2-07 — Ver detalle de un comportamiento predeterminado

**Descripción.** Dado un comportamiento predeterminado del listado, cuando el usuario lo abre, puede entender qué hace y consultar su definición según lo acordado para la interfaz.

**Notas técnicas.** El borrador de API no incluye un endpoint de detalle. Acordar si el listado trae todos los datos necesarios o si se agrega, por ejemplo, `GET /behaviours/{behaviourId}`. El detalle debe ser de solo lectura en este sprint.

**Criterios de aceptación.**

- El detalle muestra nombre, explicación y definición o código Python del comportamiento, según la decisión de producto.
- Un identificador inexistente muestra un error claro.
- Desde esta vista no se ofrecen opciones de editar ni eliminar el comportamiento.

**Dependencias:** S2-06.

**Esfuerzo orientativo:** 3/10.

### S2-08 — Configurar el equipo que se usará en ligas y amistosos

**Descripción.** Dado un club con jugadores y comportamientos, el usuario define una configuración jugable que pueda usarse al inscribirse en una liga o disputar un amistoso.

**Notas técnicas.** El alcance describe tres titulares, tres suplentes, formación y un comportamiento por jugador. La API preliminar separa `PUT /team/default` y `PUT /matches/{matchId}/lineup`; sus campos no cubren igual la asignación de comportamientos. Acordar un contrato coherente para el equipo predeterminado y, si corresponde, para la alineación previa al amistoso.

**Criterios de aceptación.**

- Se eligen exactamente tres titulares y tres suplentes distintos, todos pertenecientes al club.
- Se elige una formación permitida y un comportamiento disponible para cada jugador que participará.
- La configuración incompleta o inválida se rechaza con indicación de qué corregir.
- El equipo guardado se puede recuperar y usar al unirse a una liga o preparar un amistoso.

**Dependencias:** S2-03, S2-06.

**Esfuerzo orientativo:** 8/10.

**Subtickets propuestos:**

- **S2-08a — Guardar y consultar el equipo del club (3/10).** Definir el contrato y persistir titulares, suplentes, formación y comportamientos asignados. **Terminado cuando:** la configuración guardada se recupera sin perder datos.
- **S2-08b — Construir la interfaz de configuración del equipo (3/10).** Permitir seleccionar jugadores, formación y comportamientos, y mostrar la selección guardada. **Terminado cuando:** el usuario puede dejar un equipo listo desde la interfaz.
- **S2-08c — Validar las reglas del equipo (2/10).** Rechazar jugadores ajenos o repetidos, cantidades incorrectas, formación inválida y comportamientos no disponibles. **Terminado cuando:** ninguna configuración inválida puede persistirse mediante la interfaz ni por API.

## Ligas en espera

### S2-09 — Crear liga pública o privada

**Descripción.** Dado un usuario autenticado con club, cuando configura una liga válida, el sistema la crea en estado de espera y lo registra como creador.

**Notas técnicas.** La API preliminar propone `POST /leagues`. Revisar los campos `startDateTime` y `roundInterval`: pueden almacenarse como configuración futura, pero Sprint 2 no inicia ligas. Para una liga privada, el sistema debe generar o validar el código de acceso y mostrarlo al creador.

**Criterios de aceptación.**

- Se validan nombre, tipo público o privado, mínimo de al menos tres clubes y máximo mayor o igual al mínimo.
- Se validan los demás parámetros exigidos por el contrato que acuerde el equipo para la creación.
- La liga creada queda en espera y aparece donde corresponda; el creador puede ver su configuración.
- Una liga privada cuenta con código de acceso utilizable por otros clubes.
- No se inicia automáticamente al alcanzar el mínimo de clubes.

**Dependencias:** S2-02.

**Esfuerzo orientativo:** 6/10.

### S2-10 — Listar ligas disponibles

**Descripción.** Dado un usuario autenticado, cuando explora ligas, ve las ligas en espera a las que podría unirse.

**Notas técnicas.** La API preliminar propone `GET /leagues` con filtro opcional por nombre. Acordar qué datos de ligas privadas son visibles antes de ingresar el código.

**Criterios de aceptación.**

- Se muestran nombre, tipo, cantidad de inscriptos, cupos y estado de las ligas disponibles.
- Las ligas llenas o fuera de estado de espera no se ofrecen como disponibles para unirse.
- El filtro por nombre funciona si se incluye en el alcance acordado del listado.
- La interfaz informa cuando no hay ligas disponibles y cuando falla la consulta.

**Dependencias:** S2-09.

**Esfuerzo orientativo:** 3/10.

### S2-11 — Unirse a una liga

**Descripción.** Dado un club con equipo válido, cuando el usuario confirma la inscripción a una liga en espera con cupo, el sistema agrega el club y actualiza la ocupación.

**Notas técnicas.** La API preliminar propone `POST /leagues/{leagueId}/join` con `accessCode` opcional. La verificación de cupo y alta deben ser atómicas para resolver inscripciones simultáneas.

**Criterios de aceptación.**

- El club puede unirse a una liga pública con cupo y a una privada con código correcto.
- Se rechazan código incorrecto, liga llena, inscripción duplicada, equipo inválido y liga que no está en espera.
- Una vez unido, el club figura una sola vez y el cupo se actualiza para los demás usuarios.
- Si dos clubes intentan ocupar el último cupo, solo se acepta uno.

**Dependencias:** S2-08, S2-10.

**Esfuerzo orientativo:** 6/10.

### S2-12 — Abandonar una liga en espera

**Descripción.** Dado un club inscripto en una liga en espera, cuando su usuario confirma que desea abandonarla, el sistema remueve la inscripción y libera el cupo.

**Notas técnicas.** La API preliminar propone `POST /leagues/{leagueId}/leave`. Acordar si el creador puede abandonar su propia liga sin cancelarla, ya que cancelar ligas está fuera de Sprint 2.

**Criterios de aceptación.**

- Un club inscripto puede abandonar una liga mientras permanezca en espera.
- El club deja de figurar en el lobby y el cupo vuelve a estar disponible.
- Se rechaza la operación si el club no pertenece a la liga o si el estado ya no permite abandonarla.
- La interfaz pide confirmación antes de enviar la solicitud y refleja el resultado.

**Dependencias:** S2-11.

**Esfuerzo orientativo:** 3/10.

### S2-13 — Ver lobby de espera de una liga

**Descripción.** Dado un usuario que abre una liga en espera, el sistema le muestra el estado actual de la inscripción para saber quiénes participan y cuántos lugares quedan.

**Notas técnicas.** El borrador de API propone `GET /leagues/{leagueId}`, pero describe también fixture y tabla de posiciones, funciones que no se necesitan en esta entrega. Para Sprint 2, devolver solo los datos de lobby pertinentes.

**Criterios de aceptación.**

- Se muestran nombre, tipo, configuración relevante, creador, clubes inscriptos, mínimo, máximo y cupos restantes.
- El lobby refleja ingresos y abandonos al actualizar la información.
- La interfaz distingue si el club actual ya está inscripto y ofrece únicamente las acciones que correspondan.
- No aparecen controles para iniciar ni cancelar la liga.

**Dependencias:** S2-09, S2-11, S2-12.

**Esfuerzo orientativo:** 5/10.

## Amistosos

### S2-14 — Gestionar disponibilidad del club para amistosos

**Descripción.** Dado un usuario autenticado, el sistema permite consultar y establecer si su club está disponible para participar en amistosos.

**Notas técnicas.** El alcance exige disponibilidad para amistosos y la API preliminar propone `GET /club/me` y `PATCH /club/me` con `friendlyAvailable`. Limitar la edición de club en esta entrega a la disponibilidad necesaria, salvo que el registro requiera elegir nombre y avatar.

**Criterios de aceptación.**

- El usuario puede ver el estado de disponibilidad de su club y modificarlo.
- El servidor aplica ese estado al crear o unirse a amistosos según la regla acordada.
- No se expone una modificación de perfil de usuario desde este flujo.

**Dependencias:** S2-01, S2-02.

**Esfuerzo orientativo:** 3/10.

### S2-15 — Crear un amistoso

**Descripción.** Dado un club habilitado y con equipo válido, cuando el usuario fija un horario de inicio y confirma, el sistema crea un amistoso abierto para recibir a otro club.

**Notas técnicas.** La API preliminar propone `POST /friendly-matches` con `startDateTime`. Definir zona horaria, anticipación mínima y condiciones de conflicto con otros partidos. El amistoso se crea con el club anfitrión como primer participante.

**Criterios de aceptación.**

- Se crea un amistoso con horario válido, club anfitrión y estado de espera.
- Se rechazan horario inválido, equipo incompleto, club no disponible y conflicto con otro partido según las reglas acordadas.
- El amistoso creado puede consultarse y queda disponible para que un rival se una.
- Una operación fallida no deja un amistoso parcial.

**Dependencias:** S2-08, S2-14.

**Esfuerzo orientativo:** 6/10.

### S2-16 — Listar amistosos disponibles

**Descripción.** Dado un usuario autenticado, cuando explora amistosos, ve aquellos abiertos a los que todavía puede unirse.

**Notas técnicas.** La API preliminar propone `GET /friendly-matches`. El listado debe distinguir estado y horario para no ofrecer un partido que ya comenzó, venció o se completó.

**Criterios de aceptación.**

- Se muestran anfitrión, horario y estado de cada amistoso disponible.
- Los amistosos completos, iniciados, finalizados, cancelados o vencidos no figuran como opciones para unirse.
- La interfaz contempla lista vacía y error de carga.

**Dependencias:** S2-15.

**Esfuerzo orientativo:** 3/10.

### S2-17 — Unirse a un amistoso

**Descripción.** Dado un club habilitado y con equipo válido, cuando el usuario elige un amistoso abierto creado por otro club y confirma, el sistema lo registra como segundo participante.

**Notas técnicas.** La API preliminar propone `POST /friendly-matches/{matchId}/join`. La ocupación del segundo lugar debe resolverse atómicamente.

**Criterios de aceptación.**

- El club queda registrado como rival y ambos participantes pueden ver el amistoso actualizado.
- El anfitrión no puede unirse a su propio amistoso y no se acepta un tercer club.
- Se rechazan club no disponible, equipo inválido, horario vencido y amistoso fuera de estado de espera.
- Si dos clubes intentan ocupar el segundo lugar al mismo tiempo, solo uno queda inscripto.

**Dependencias:** S2-08, S2-14, S2-16.

**Esfuerzo orientativo:** 5/10.

### S2-18 — Preparar y fijar las alineaciones del amistoso

**Descripción.** Dado un amistoso con dos participantes, cada club dispone de una alineación completa antes del inicio. Al comenzar, jugadores y comportamientos quedan fijados para todo el partido.

**Notas técnicas.** Puede usarse el equipo predeterminado de S2-08 o permitir ajustes previos mediante `PUT /matches/{matchId}/lineup`, como sugiere el borrador de API. La consigna solo excluye cambios *durante* el partido; confirmar si los ajustes previos son obligatorios en Sprint 2.

**Criterios de aceptación.**

- Ambos clubes tienen exactamente tres titulares, tres suplentes, formación y comportamiento válido para cada jugador requerido.
- Solo se aceptan jugadores y comportamientos propios o disponibles para el club correspondiente.
- El partido no comienza con una configuración incompleta.
- Tras el inicio no se pueden modificar alineaciones ni comportamientos desde la interfaz de Sprint 2.

**Dependencias:** S2-08, S2-17.

**Esfuerzo orientativo:** 5/10.

## Partido y observación

### S2-19 — Iniciar el amistoso y resolver la ausencia de rival

**Descripción.** Dado un amistoso programado, el sistema decide su transición al llegar el horario: comienza si tiene dos clubes y configuraciones válidas, o se cancela si no consiguió rival.

**Notas técnicas.** El borrador de API no define un endpoint de inicio de amistoso. Acordar si el inicio es automático por horario o por acción de un usuario autorizado. El alcance general menciona inicio por horario; esta propuesta lo toma como supuesto provisional. La transición debe ejecutarse una sola vez.

**Criterios de aceptación.**

- Un amistoso con dos clubes y equipos válidos pasa una sola vez al estado de juego al cumplirse la condición de inicio acordada.
- Un amistoso sin rival al vencimiento pasa a cancelado y no puede aceptar participantes.
- No se crean dos simulaciones del mismo partido ante procesos o solicitudes simultáneas.
- Ambos clubes pueden ver el nuevo estado.

**Dependencias:** S2-17, S2-18.

**Esfuerzo orientativo:** 6/10.

### S2-20 — Ejecutar comportamientos durante el partido

**Descripción.** Dado un amistoso en juego, el motor invoca el comportamiento seleccionado para cada jugador cuando corresponde y aplica sus acciones válidas a la simulación.

**Notas técnicas.** Este ticket debe respetar la API de comportamientos acordada en S2-05. Definir cómo se limita el tiempo y los recursos de ejecución de Python y qué hace el motor cuando un comportamiento falla o devuelve una acción inválida. No incluye editar comportamientos ni cambiar su asignación en pleno partido.

**Criterios de aceptación.**

- Se ejecutan los comportamientos fijados al inicio con el estado de juego que prescribe su API.
- Las acciones válidas afectan al partido de manera observable y consistente.
- Un error o salida inválida de un comportamiento se maneja de forma definida sin dejar el partido bloqueado.
- Una prueba integrada verifica que los tres comportamientos predeterminados pueden ejecutarse.

**Dependencias:** S2-05, S2-19.

**Esfuerzo orientativo:** 9/10.

**Subtickets propuestos:**

- **S2-20a — Invocar los comportamientos con el estado del partido (3/10).** Preparar la entrada definida en S2-05a, ejecutar el comportamiento asignado y recoger su acción. **Terminado cuando:** el motor puede invocar cualquiera de los tres comportamientos predeterminados en una situación de partido.
- **S2-20b — Aplicar al juego las acciones válidas (4/10).** Traducir las acciones devueltas por los comportamientos a cambios de posición, pelota u otros elementos definidos por las reglas. **Terminado cuando:** una acción válida produce un cambio observable y coherente en el estado del partido.
- **S2-20c — Manejar fallos y límites de ejecución (2/10).** Controlar errores, salidas inválidas y tiempos o recursos excedidos conforme a la política acordada. **Terminado cuando:** un comportamiento fallido no bloquea ni corrompe el partido.

### S2-21 — Simular el amistoso completo y conservar el resultado

**Descripción.** Dado un amistoso iniciado, el sistema hace avanzar el juego, actualiza el estado y llega a un resultado final persistido sin intervención de los usuarios.

**Notas técnicas.** Acordar duración y ritmo de simulación para Sprint 2. Aunque el alcance general menciona entretiempo y pausas, la consigna de esta entrega los excluye; la simulación de Sprint 2 debe poder completarse sin depender de esas mecánicas. Definir reglas mínimas de pelota, desplazamiento, goles y fin de partido para que la observación sea significativa.

**Criterios de aceptación.**

- El estado avanza desde inicio hasta final y el marcador cambia cuando ocurre un gol válido.
- El partido termina automáticamente y registra resultado, participantes y tiempo final.
- Una vez finalizado, no se ejecutan más acciones ni se modifica el resultado.
- Se puede reproducir una prueba de punta a punta que llega al final sin pausas, sustituciones ni controles tácticos.

**Dependencias:** S2-20.

**Esfuerzo orientativo:** 9/10.

**Subtickets propuestos:**

- **S2-21a — Avanzar y conservar el estado de juego (3/10).** Implementar el ciclo de simulación, el reloj y la evolución del estado entre actualizaciones. **Terminado cuando:** un amistoso iniciado avanza sin intervención de los usuarios.
- **S2-21b — Resolver las reglas mínimas del partido y los goles (4/10).** Aplicar las reglas de movimiento, pelota y anotación que se acuerden para Sprint 2. **Terminado cuando:** el marcador cambia únicamente por goles válidos y el estado conserva coherencia.
- **S2-21c — Finalizar y persistir el resultado (2/10).** Detener la simulación al concluir la duración acordada y guardar el resultado. **Terminado cuando:** el partido pasa a finalizado una sola vez y su resultado puede consultarse después.

### S2-22 — Consultar el estado actual y final de un partido

**Descripción.** Dado un partido existente, el cliente puede recuperar una representación suficiente para mostrar lo que ocurre y, después, consultar su resultado final.

**Notas técnicas.** La API preliminar propone `GET /matches/{matchId}`. Acordar el contrato de estado: clubes, jugadores titulares, posiciones, pelota, marcador, reloj y estado del partido. Elegir mecanismo de actualización de la interfaz, por ejemplo consultas periódicas o eventos, sin exigir una tecnología particular en el ticket.

**Criterios de aceptación.**

- La consulta devuelve un estado coherente con la simulación en curso y distingue espera, juego, cancelación y finalización.
- Incluye los datos necesarios para renderizar la interfaz de observación acordada.
- El estado final sigue disponible luego de terminar el partido.
- Un identificador inexistente o acceso no permitido se maneja con una respuesta clara.

**Dependencias:** S2-19, S2-21.

**Esfuerzo orientativo:** 5/10.

### S2-23 — Construir la interfaz completa para observar amistosos

**Descripción.** Dado un usuario que abre un amistoso, la interfaz muestra el estado de espera, el partido en vivo y el resultado final de forma comprensible.

**Notas técnicas.** La consigna exige toda la interfaz para observar amistosos. La representación exacta de la cancha puede acordarse con los profes, pero debe mostrar el estado que produce el motor y actualizarse durante el juego sin que el usuario refresque manualmente la página.

**Criterios de aceptación.**

- La vista permite identificar clubes participantes, jugadores en cancha, pelota, marcador, tiempo y estado del partido.
- La información visible se actualiza durante el partido y coincide con el estado informado por el servidor.
- Se muestran claramente espera, cancelación, juego y resultado final.
- Se contemplan errores de carga y reconexión o recuperación de la vista si se interrumpe la actualización.
- No se muestran controles de pausa, sustitución o cambio de comportamiento durante el partido.

**Dependencias:** S2-22.

**Esfuerzo orientativo:** 8/10.

**Subtickets propuestos:**

- **S2-23a — Mostrar datos y estados del amistoso (3/10).** Construir la vista de participantes, marcador, tiempo, espera, cancelación y finalización. **Terminado cuando:** cada estado tiene una presentación comprensible con datos reales del servidor.
- **S2-23b — Representar el juego en vivo (3/10).** Mostrar cancha, jugadores y pelota usando el estado recibido y actualizar su representación durante el juego. **Terminado cuando:** el observador ve la evolución del partido sin refrescar manualmente.
- **S2-23c — Recuperar la vista ante errores de actualización (2/10).** Mostrar errores de carga y permitir retomar la observación tras una interrupción. **Terminado cuando:** una falla temporal no deja al usuario mirando datos antiguos como si fueran actuales.

### S2-24 — Verificar el recorrido integrado de Sprint 2

**Descripción.** Dado el sistema implementado, el equipo valida el recorrido completo de la entrega con más de un usuario y documenta los resultados de la prueba.

**Notas técnicas.** Este ticket busca detectar problemas entre módulos, no reemplazar las verificaciones particulares de cada ticket. Conviene usar datos de prueba reproducibles y registrar los casos fallidos relevantes.

**Criterios de aceptación.**

- Dos usuarios se registran, inician sesión, ven los comportamientos predeterminados y preparan equipos válidos.
- Se crea una liga, se lista, otro club se une, el lobby cambia y ese club puede abandonarla.
- Se crea un amistoso, se lista, el segundo club se une, el partido comienza, ejecuta comportamientos y llega a un resultado final.
- Ambos clubes pueden observar el amistoso y consultar el resultado final.
- Se verifican al menos las restricciones críticas: PACSS inválido, código privado incorrecto, cupo ocupado, equipo incompleto y unión tardía a un amistoso.

**Dependencias:** S2-01 a S2-23.

**Esfuerzo orientativo:** 5/10.

## Preguntas concretas para los profes

1. ¿Cuál es el contrato exacto de la API de comportamientos en Python: entrada, salida, primitivas, límites de ejecución y manejo de errores?
2. ¿Cómo se inicia un amistoso en esta entrega: automáticamente en el horario configurado o mediante una acción? ¿Qué pasa si uno de los clubes no está conectado?
3. ¿Se exige permitir ajustes de alineación antes de cada amistoso o basta con el equipo predeterminado?
4. ¿Qué datos y nivel de animación deben verse en la interfaz del partido para considerar cumplido “observar amistosos”?
5. ¿Qué parámetros de creación de liga siguen siendo obligatorios si no se podrán iniciar ligas en Sprint 2? ¿Puede el creador abandonar su liga?
6. ¿Cómo deben verse las ligas privadas en el listado antes de ingresar su código?

## Escala de esfuerzo y reparto orientativo

El esfuerzo de cada ticket está expresado de **1 a 10**: 1 sería una tarea pequeña y conocida; 10, una tarea grande, con varias reglas, integraciones o incertidumbre. **No son horas ni puntos de historia**, y sumar estos valores solo sirve para comparar repartos iniciales. Los 24 tickets suman **130 unidades orientativas**. Conviene revisarlas después de responder las preguntas para los profes y de comprobar qué código ya existe.

Los tickets de 7/10 o más tienen subtickets propuestos. **El esfuerzo del ticket padre es la suma orientativa de sus subtickets: no debe sumarse dos veces.** Al pasarlos a Jira, el padre puede funcionar como agrupador y cada subticket tener responsable propio. Las tablas de abajo siguen agrupando los 24 tickets padre para mostrar una distribución inicial; los subtickets permiten afinarla y repartir partes de un mismo padre entre varias personas.

Las letras indican personas hipotéticas, no responsables asignados. Una persona coordina cada ticket padre, pero sus subtickets pueden repartirse entre integrantes distintos. Se mantuvieron los mismos 24 tickets padre en las tres opciones.

### Si trabajan 6 personas

| Persona | Tickets | Suma |
| --- | --- | ---: |
| A | S2-01 a S2-04: cuenta y plantel | 21 |
| B | S2-05 a S2-08: comportamientos y equipo | 22 |
| C | S2-09 a S2-13: ligas en espera | 23 |
| D | S2-14 a S2-18: amistosos y alineaciones | 22 |
| E | S2-19 a S2-21: inicio y motor del partido | 24 |
| F | S2-22 a S2-24: consulta, interfaz y prueba integrada | 18 |

### Si trabajan 5 personas

| Persona | Tickets | Suma |
| --- | --- | ---: |
| A | S2-01 a S2-03, S2-22 y S2-23: cuenta, plantel y observación | 29 |
| B | S2-04 a S2-08: crear jugador, comportamientos y equipo | 27 |
| C | S2-09, S2-11 a S2-13 y S2-24: ligas y prueba integrada | 25 |
| D | S2-10, S2-14 a S2-18: listados y amistosos | 25 |
| E | S2-19 a S2-21: inicio y motor del partido | 24 |

### Si trabajan 4 personas

| Persona | Tickets | Suma |
| --- | --- | ---: |
| A | S2-01 a S2-04, S2-22 y S2-23: cuenta, plantel y observación | 34 |
| B | S2-05 a S2-08, S2-12, S2-16 y S2-24: comportamientos, equipo, vistas y prueba integrada | 33 |
| C | S2-09 a S2-11, S2-13 a S2-15: ligas y creación de amistosos | 29 |
| D | S2-17 a S2-21: inscripción, alineaciones e implementación del partido | 34 |

**Orden sugerido.** Acordar primero el contrato de comportamientos, equipo y estado de partido. Después pueden avanzar en paralelo cuenta/plantel, ligas, amistosos y motor. La persona a cargo de S2-24 coordina la prueba integrada con todas las demás; no debería esperar al último día para comenzar. En el reparto de cuatro personas, S2-16 depende de S2-15 y S2-22/23 dependen del motor: esos cruces requieren coordinación temprana.
