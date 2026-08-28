# Casos de Uso - FutBot
 **Versión:** 0.1


### Módulo: Autenticación y Cuenta
* **CU01:** Registrar nuevo usuario

* **Actor:** Visitante
* **Precondición:** El visitante no ha iniciado sesión en el sistema
* **escenario exitoso Principal:**
  1. El visitante accede a la vista de registro
  2. El sistema presenta el formulario de registro solicitando: nombre completo, nombre de usuario (`username`), correo electrónico (`email`), contraseña (`password`) 
  3. El visitante completa los campos y envía el formulario
  4. El sistema valida los datos:
     * El formato del correo electrónico es válido y no está registrado previamente
     * El nombre de usuario es único
  5. El sistema crea la cuenta del `Usuario`
  6. El sistema crea automáticamente la entidad `Club` asociada al nuevo usuario (con un nombre por defecto derivado del usuario o solicitado en el formulario)
  7. El sistema redirige al usuario al panel principal de su club
* **casos excepcionales:**
  * **4a. Datos duplicados (Email o Username ya existentes):** El sistema notifica que el correo o nombre de usuario ya están en uso y solicita ingresar valores diferentes
  * **4c. Campos obligatorios vacíos o inválidos:** El sistema resalta los campos con error y detiene el flujo


* **CU02:** Iniciar sesión 

* **Actor:** Usuario registrado 
* **Precondición:** El usuario posee una cuenta registrada en el sistema y no tiene una sesión activa en el cliente
* **escenario exitoso principal:**
  1. El usuario accede a la pantalla de inicio de sesión
  2. El sistema solicita: correo electrónico (`email`) y contraseña (`password`)
  3. El usuario ingresa sus datos y presiona "Iniciar Sesión"
  4. El sistema valida que el correo exista y que el hash de la contraseña coincida con el registrado en la base de datos
  5. El sistema redirige al usuario a la vista principal de su club
* **escenarios excepcionales:**
  * **4a. Credenciales inválidas:** El sistema muestra un mensaje de error genérico (*"Correo o contraseña incorrectos"*) por motivos de seguridad y permite reintentar el ingreso.
  * **4b. Cuenta inexistente:** Si el correo no figura en el sistema, se muestra el mismo mensaje de error genérico que en 4a

* **CU03:** Configurar / Modificar avatar del club
* **Actor:** Usuario autenticado
* **Precondición:** El usuario ha iniciado sesión y administra su club
* **Escenario exitoso principal:**
  1. El usuario ingresa a la sección de configuración de su club
  2. El usuario selecciona un nuevo avatar de la galería disponible y confirma el cambio.
  3. El sistema valida la selección y actualiza el identificador del avatar 
  4. El sistema actualiza la interfaz visual del usuario reflejando el nuevo avatar y confirma que los cambios fueron guardados exitosamente
* **escenarios excepcionales:**
  * **3a. Cancelar selección:** El usuario decide no modificar el avatar y cierra el selector; el sistema mantiene el avatar previo sin registrar cambios

* **CU04:** Cerrar sesión 
* **Actor:** Usuario autenticado
* **Precondición:** El usuario cuenta con una sesión activa en la aplicación
* **escenario exitoso principal :**
  1. El usuario presiona el botón "Cerrar Sesión" desde el menú de navegación o perfil
  2. El sistema invalida la sesión activa.
  3. El sistema redirige al usuario a la página de inicio/login para visitantes
* **escenarios excepcionales:**
  * No presenta(el cierre de sesión local es inmediato)

* **CU05:** Consultar perfil de club rival
* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa y visualiza un listado público (ranking, fixture de liga)
* **escenario exitoso principal:**
  1. El usuario selecciona el nombre o avatar de un club rival
  2. El sistema recupera y muestra la información pública del club:
     * Nombre del club y avatar actual
     * Estadísticas generales (partidos jugados, victorias, empates, derrotas, posición en el ranking global)
     * Plantilla de jugadores del club con sus respectivos nombres y atributos PACSS
  3. El usuario visualiza la ficha técnica del rival sin acceso a su código fuente ni tácticas privadas
* **escenarios excepcioanales:**
  * **2a. Club no encontrado:** El sistema muestra una notificación informando que el club solicitado no se encuentra disponible y regresa a la vista anterior

### Módulo: Sistema de Amigos ?? nose si esta confirmado esto
* **CU06:** Buscar usuario por username
* **CU07:** Enviar solicitud de amistad
* **CU08:** Aceptar / Rechazar solicitud de amistad
* **CU09:** Listar amigos y solicitudes pendientes 


### Módulo: Gestión de Plantel y Comportamientos
* **CU10:** Crear jugador (Validación PACSS: suma 300, rango 20-100)

* **Actor:** Usuario autenticado.
* **Precondición:** El usuario ha iniciado sesión y administra su club
* **escenario exitoso principal:**
  1. El usuario accede a la sección para "Crear Jugador"
  2. El sistema despliega un formulario solicitando:
     * Nombre del jugador
     * Asignación de puntos para cada atributo PACSS: Power, Agility, Control, Speed y Strength
  3. El usuario ingresa el nombre y distribuye los puntos entre los 5 atributos
  4. El usuario confirma la creación presionando "Guardar"
  5. El sistema valida las reglas de negocio PACSS:
     * El nombre no está vacío.
     * Cada uno de los 5 atributos es un número entero dentro del rango $[20, 100]$
     * La sumatoria estricta de los 5 atributos es exactamente igual a $300$ 
  6. El sistema crea la entidad `Jugador` asociada al `Club` del usuario
  7. El sistema confirma la creación y actualiza la lista de jugadores disponibles en el plantel
* **escenarios excepcionales:**
  * **5a. Sumatoria de PACSS distinta de 300:** El sistema bloquea el guardado e indica visualmente la cantidad de puntos sobrantes o faltantes para alcanzar exactamente los 300 puntos requeridos
  * **5b. Atributo fuera del rango permitido ($< 20$ o $> 100$):** El sistema resalta los campos fuera de rango y exige corregirlos antes de continuar
  * **5c. Nombre no provisto:** El sistema solicita completar el campo obligatorio del nombre


* **CU11:** Listar jugadores del club

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa
* **escenario exitoso principal:**
  1. El usuario navega al apartado del plantel
  2. El sistema consulta la base de datos y recupera todos los jugadores activos (no eliminados lógicamente) pertenecientes al club del usuario
  3. El sistema muestra una vista con las tarjetas o tabla de cada jugador, mostrando:
     * Nombre del jugador.
     * Desglose de sus 5 atributos PACSS (Power, Agility, Control, Speed, Strength)
     * Indicador de estado (disponible / inscripto en liga)
* **escenarios excepcionales:**
  * **2a. El club no posee jugadores creados:** El sistema muestra una vista vacía y un botón de acceso directo a "Crear Jugador"

* **CU12:** Eliminar jugador del club 

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa y visualiza el listado de su plantel
* **escenario exitoso principal:**
  1. El usuario selecciona la opción "Eliminar" en un jugador específico
  2. El sistema verifica que el club **no posea ningún partido en curso** en ese momento
  3. El sistema solicita confirmación mediante un cuadro de diálogo advirtiendo que la acción dará de baja al jugador de la plantilla activa
  4. El usuario confirma la eliminación
  5. El sistema realiza una baja del jugador (marca su estado como inactivo/eliminado para que no aparezca en futuros listados ni nuevas inscripciones)
  6. Si el jugador formaba parte de una liga en curso, sus datos se mantienen intactos como snapshot (`JugadorInscriptoLiga`) dentro del torneo correspondiente
  7. El sistema confirma la eliminación y refresca el listado del plantel
* **escenarios excepcionales:**
  * **2a. Club con partido en curso:** El sistema bloquea la operación y notifica: *"No se pueden eliminar jugadores mientras el club tenga un partido en disputa"*
  * **4a. Cancelación:** El usuario cancela el diálogo de confirmación; el sistema no realiza cambios y mantiene al jugador activo


* **CU13:** Crear comportamiento 

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa
* **escenario exitoso principal:**
  1. El usuario accede a la sección "Comportamientos" y presiona "Nuevo Comportamiento"
  2. El sistema comprueba que el club **no tenga partidos en curso**
  3. El sistema presenta la interfaz con:
     * Campo para el nombre del comportamiento
     * Entorno de edición lógica
  4. El usuario ingresa un nombre y diseña la secuencia lógica
  5. El usuario presiona "Guardar Comportamiento"
  6. El sistema valida que el nombre no esté vacío y compila/valida la estructura lógica 
  7. El sistema almacena el nuevo `Comportamiento` asociado al club.
  8. El sistema notifica el guardado exitoso y añade el script al listado de tácticas disponibles.
* **escenarios alternativos:**
  * **2a. Club con partido en curso:** El sistema bloquea el acceso a la creación de comportamientos hasta que finalice el encuentro.
  * **6a. Estructura de bloques incompleta o errónea:** El sistema resalta los bloques desconectados o inválidos e impide el guardado hasta su corrección

* **CU14:** Editar comportamiento (solo si no hay partido en curso)
* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa y al menos un comportamiento creado
* **escenario exitoso principal:**
  1. El usuario ingresa al listado de comportamientos y presiona "Editar" sobre uno existente
  2. El sistema comprueba que el club **no tenga partidos en curso**
  3. El sistema carga en el editor de bloques el nombre y la lógica actual del comportamiento
  4. El usuario realiza las modificaciones deseadas y actualiza
  5. El sistema valida la consistencia de lo modificado
  6. El sistema actualiza el código del `Comportamiento` en la base de datos del club
  7. El sistema confirma la actualización e informa que el cambio aplicará a futuras asignaciones y partidos (sin alterar ligas ya congeladas)
* **escenario alternativo:**
  * **2a. Club con partido en curso:** El sistema desactiva la opción de edición y muestra un mensaje informando que no es posible modificar scripts mientras haya partidos en juego.
  * **5a. Error en la estructura de bloques:** El sistema marca los errores lógicos y solicita repararlos antes de realizar cambios

* **CU15:** Eliminar comportamiento 
* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa y visualiza sus comportamientos
* **escenario exitoso principal:**
  1. El usuario presiona el botón "Eliminar" en un comportamiento especifico
  2. El sistema comprueba que el club **no tenga partidos en curso**
  3. El sistema solicita confirmación al usuario para proceder con el borrado
  4. El usuario confirma la eliminación
  5. El sistema ejecuta una baja del comportamiento
  6. El sistema notifica la eliminación exitosa y lo retira del listado activo
* **escenarios excepcionales:**
  * **2a. Club con partido en curso:** El sistema bloquea la eliminación notificando la restricción de partidos activos
  * **4a. Cancelación:** El usuario cancela y el comportamiento permanece activo

* **CU16:** Listar comportamientos del club
* **Actor:** Usuario autenticado.
* **Precondición:** El usuario ha iniciado sesión
* **escenario exitoso principal:**
  1. El usuario ingresa a la sección "Comportamientos"
  2. El sistema recupera de la base de datos todos los comportamientos vigentes asociados al club del usuario.
  3. El sistema muestra la lista de tácticas con su nombre, fecha de creación/modificación y las opciones de "Editar", "Ver" o "Eliminar".
* **escenarios excepcioanles:**
  * **2a. No existen comportamientos registrados:** El sistema muestra un mensaje indicando que el club aún no posee tácticas creadas junto a un botón para crear la primera

### Módulo: Ligas y Torneos
* **CU17:** Crear liga (pública o privada con código, min/max clubes >= 3, duración)

* **Actor:** Usuario autenticado (Club Creador).
* **Precondición:** El usuario ha iniciado sesión
* **escenario exitoso principal:**
  1. El usuario accede a la sección "Ligas" y crea una
  2. El sistema despliega el formulario de configuración solicitando:
     * Nombre de la liga.
     * Tipo de accesibilidad: Pública o Privada (con código/contraseña de acceso o invitación).
     * Cantidad mínima de clubes (por defecto 3, configurable a un valor mayor o igual a 3)
     * Cantidad máxima de clubes
     * Duración de los partidos.  ??
  3. El usuario completa los parámetros y confirma la creación.
  4. El sistema valida las reglas de negocio:
     * El nombre no está vacío
     * La cantidad mínima es 3
     * La cantidad máxima es mayor o igual a la mínima
     * Si es privada, se genera o valida el código de acceso
  5. El sistema crea la entidad `Liga` en estado `ABIERTA` asignando al club del usuario como creador (owner)
  6. El sistema inscribe automáticamente al club creador como primer participante (solicitando los datos de inscripción del CU19)
* **escenarios excepcionales:**
  * **4a. Mínimo de clubes menor a 3:** El sistema advierte que el cupo mínimo permitido es de 3 clubes e impide guardar.
  * **4b. Máximo menor al mínimo:** El sistema notifica la inconsistencia en los cupos y solicita corregir los valores

* **CU18:** Listar y buscar ligas disponibles

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa
* **escenario exitoso principal:**
  1. El usuario abre "Explorar Ligas"
  2. El sistema consulta y presenta la lista de ligas en estado `ABIERTA` y con cupos disponibles.
  3. Para cada liga, el sistema muestra: nombre, tipo (pública/privada), creador, cupos ocupados/totales (ej: 4/8) y duración de partidos
  4. El usuario puede filtrar por nombre o visibilidad
  5. El sistema actualiza la lista según los filtros aplicados
* **escenarios excepcionales:**
  * **2a. No hay ligas disponibles con cupo abierto:** El sistema muestra un mensaje indicando que no se encontraron ligas abiertas y ofrece la opción de "Crear Liga"

* **CU19:** Inscribirse a una liga (selección de 6 jugadores, formación y tácticas iniciales)
* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa. El club posee al menos 6 jugadores y 1 comportamiento. La liga está en estado `ABIERTA` y no ha alcanzado el cupo máximo.
* **escenario exitoso principal:**
  1. El usuario selecciona una liga y presiona "Unirse"
  2. Si la liga es privada, el sistema solicita ingresar el código de acceso. El usuario lo ingresa y el sistema valida que coincida
  3. El sistema presenta la pantalla de configuración de plantel para la liga
  4. El usuario selecciona exactamente 6 jugadores de su club.
  5. El usuario define la alineación por defecto para el torneo: 3 titulares, 3 suplentes, la formación táctica y asigna un comportamiento a cada jugador
  6. El usuario confirma la inscripción
  7. El sistema valida que el club no esté previamente inscripto y que la configuración contenga exactamente 6 jugadores válidos con comportamientos
  8. El sistema registra la `ParticipacionLiga` y genera las copias inmutables de los 6 jugadores (`JugadorInscriptoLiga`) y sus comportamientos guardados para la liga
  9. Si con esta inscripción se alcanza el cupo máximo de clubes, el sistema bloquea nuevas uniones y deja la liga a la espera de ser iniciada
* **escenarios excepcionales:**
  * **2a. Código de acceso incorrecto:** El sistema deniega el acceso e informa el error
  * **7a. Plantel incompleto:** El sistema notifica que deben seleccionarse exactamente 6 jugadores (3 titulares y 3 suplentes) con sus respectivos scripts
  * **9a. Liga llena simultáneamente:** Si otro club ocupó el último cupo instantes antes, el sistema notifica que la liga se ha completado


* **CU20:** Abandonar liga (solo antes del inicio)

* **Actor:** Usuario autenticado (Club participante, no creador)
* **Precondición:** El club está inscripto en una liga que se encuentra en estado `ABIERTA` (no ha sido iniciada)
* **escenario exitoso principal:**
  1. El usuario accede al detalle de la liga en la que está inscripto
  2. El usuario selecciona la opción "Abandonar Liga"
  3. El sistema solicita confirmación de la baja
  4. El usuario confirma la acción
  5. El sistema elimina la `ParticipacionLiga` del club, libera el cupo y reactiva la posibilidad de que otros clubes se unan
  6. El sistema confirma la desvinculación y redirige al usuario a su panel principal
* **escenarios excepcionales:**
  * **2a. La liga ya fue iniciada:** El sistema oculta/bloquea el botón de abandono y muestra un mensaje informando que no es posible retirarse de un torneo en curso


* **CU21:** Iniciar liga (Creador, con cupo mínimo alcanzado)

* **Actor:** Usuario autenticado (Club Creador).
* **Precondición:** La liga está en estado `ABIERTA` y la cantidad de clubes inscriptos es mayor o igual a la cantidad mínima configurada
* **escenario exitoso principal:**
  1. El creador accede al panel de administración de su liga.
  2. El sistema habilita el botón "Iniciar Liga" al constatar que se cumple el cupo mínimo.
  3. El creador presiona "Iniciar Liga"
  4. El sistema cambia el estado de la liga a `INICIADA`.
  5. El sistema genera automáticamente el `Fixture` con el calendario completo de partidos en formato todos contra todos, agrupándolos por rondas
  6. El sistema inicializa la `TablaDePuntaje` con todos los clubes inscriptos en 0 puntos.
  7. El sistema notifica a todos los participantes e inicia la cuenta regresiva para la primera ronda de partidos simultáneos.
* **escenarios excepcionales:**
  * **2a. No se alcanza el cupo mínimo de clubes:** El botón permanece deshabilitado informando cuántos clubes faltan para poder arrancar

* **CU22:** Cancelar liga (Creador, antes del inicio)
* **Actor:** Usuario autenticado (Club Creador)
* **Precondición:** La liga se encuentra en estado `ABIERTA` (aún no ha iniciado)
* **escenario exitoso principal:**
  1. El creador accede al panel de la liga y presiona "Cancelar Liga".
  2. El sistema muestra una advertencia indicando que la liga será cancelada y se removerán todos los clubes inscriptos.
  3. El creador confirma la cancelación.
  4. El sistema cambia el estado de la liga a `CANCELADA`, disuelve las participaciones y desactiva el acceso.
  5. El sistema notifica la cancelación y redirige al creador a su panel.
* **escenarios excepcionales:**
  * **1a. La liga ya inició:** El sistema impide la cancelación una vez que el torneo está en juego


* **CU23:** Ver fixture, rondas y tabla de posiciones de la liga

* **Actor:** Usuario autenticado
* **Precondición:** El usuario accede al detalle de una liga iniciada o finalizada.
* **escenario exitoso principal:**
  1. El usuario ingresa a la liga deseada
  2. El sistema presenta dos pestañas principales:
     * **Fixture / Rondas:** Muestra los enfrentamientos de cada ronda, indicando si los partidos están programados, en curso (con marcador en vivo) o finalizados (con resultado final).
     * **Tabla de Posiciones:** Muestra la lista de clubes ordenada por: Puntos,Diferencia de Gol,Goles a Favor,Partidos Ganados/Empatados/Perdidos
  3. El usuario puede alternar entre rondas o hacer clic en un partido en vivo para ir a observarlo
* **escenario excepcionales:**
  * No presenta

* **CU24:** Finalizar liga (automático tras la última ronda)

* **Actor:** Sistema de Simulación (Automático)
* **Precondición:** La liga está en estado `INICIADA` y se ha simulado y registrado el resultado del último partido de la última ronda del fixture
* **escenario exitoso principal:**
  1. El sistema de simulación detecta que todos los partidos del fixture han pasado a estado `FINALIZADO`
  2. El sistema actualiza la tabla de posiciones con los resultados de la última fecha y determina las posiciones finales definitivas
  3. El sistema cambia el estado de la liga a `FINALIZADA`
  4. Si la liga era de tipo **Pública**, el sistema calcula y transfiere los puntos obtenidos por cada club a la tabla de **Ranking Global**
  5. El sistema emite una notificación a todos los participantes con el resultado final del torneo
* **escenarios excepcionales:**
  * **4a. Liga Privada:** El sistema finaliza la liga pero no otorga ni modifica los puntos del Ranking Global   

### Módulo: Partidos y Simulación        (asumiendo que existe el sistema de amigos)
* **CU25:** Enviar desafío de partido amistoso a un amigo

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa. El club posee al menos 6 jugadores y 1 comportamiento. El destinatario pertenece a la lista de amigos del usuario
* **escenario exitoso principal:**
  1. El usuario accede a su lista de amigos y presiona el botón "Desafiar" junto al amigo elegido
  2. El sistema despliega el formulario de configuración del partido amistoso solicitando:
     * Duración total del partido
     * Selección de los 6 jugadores (3 titulares y 3 suplentes)
     * Selección de la formación táctica y asignación de comportamientos a los jugadores
  3. El usuario completa los parámetros y envía el desafío
  4. El sistema valida que el club cumpla con la plantilla de 6 jugadores válidos con tácticas asignadas
  5. El sistema crea el partido en estado `PROGRAMADO` (modo amistoso) y envía la notificación/solicitud al amigo destinatario
  6. El sistema confirma el envío y deja el desafío en estado "Esperando respuesta"
* **escenarios excepcionales:**
  * **2a. Plantel incompleto:** El sistema notifica que deben asignarse exactamente 3 titulares, 3 suplentes y sus respectivos comportamientos para poder enviar la invitación

* **CU26:** Aceptar / Rechazar desafío de partido amistoso

* **Actor:** Usuario autenticado (amigo desafiado)
* **Precondición:** El usuario ha recibido una invitación de partido amistoso pendiente
* **escenario exitoso principal(Aceptación):**
  1. El usuario accede a su bandeja de solicitudes de amistosos
  2. El sistema muestra los detalles de la invitación: club retador y duración del partido
  3. El usuario presiona "Aceptar desafío"
  4. El sistema solicita al usuario configurar su propia alineación para el amistoso (3 titulares, 3 suplentes, formación y comportamientos)
  5. El usuario confirma su alineación
  6. El sistema valida los datos, empareja ambos clubes y programa la simulación del partido
  7. El sistema notifica a ambos usuarios y habilita el enlace para observar el partido en vivo
* **escenarios excepcionales:**
  * **3a. Rechazar desafío:** El usuario presiona "Rechazar" el sistema cancela la solicitud, elimina el partido programado y notifica al otro usuario

* **CU27:** Configurar alineación previa al partido (titulares, suplentes y formación ?? )

* **Actor:** Usuario autenticado.
* **Precondición:** El club tiene un partido programado (de liga o amistoso) que aún no ha comenzado.
* **Flujo Principal:**
  1. El usuario accede al detalle de su próximo partido.
  2. El sistema carga la alineación por defecto del club (los 6 jugadores inscriptos en la liga o los configurados en el amistoso).
  3. El usuario hace cambios previos:
     * Intercambia qué jugadores arrancan como titulares y cuáles como suplentes
     * Selecciona la formación táctica ?? 
     * Modifica los scripts de comportamiento asignados a cada titular
  4. El usuario presiona "Guardar Alineación".
  5. El sistema valida que haya exactamente 3 titulares y 3 suplentes, y que cada titular tenga un comportamiento asignado.
  6. El sistema guarda la configuración táctica específica para ese encuentro ??
* **escenarios excepcioanles:**
  * **2a. El usuario no interviene:** Si el usuario no modifica la alineación antes de la hora de inicio, el sistema inicia el partido automáticamente utilizando la configuración por defecto guardada en la inscripción

* **CU28:** Observar partido en vivo   (a reveer)
* **Actor:** Usuario autenticado / Visitante
* **Precondición:** El partido se encuentra en estado `EN_CURSO`
* **escenario exitoso principal:**
  1. El usuario accede a la vista de la cancha del partido en disputa.
  2. El cliente web (React) establece una conexión de tiempo real (**WebSocket**) 
  3. El servidor simula el encuentro paso a paso (ticks) y transmite periódicamente el estado completo del juego:
     * Coordenadas (X, Y) y vector de movimiento de la pelota.
     * Posición, orientación y acción actual (corriendo, pateando..) de los 6 jugadores en cancha
     * Cuarto actual (1 a 4), tiempo restante y marcador en vivo
  4. La interfaz en React recibe los mensajes y redibuja la animación de la cancha y el marcador en tiempo real sin recargar la página
  5. El usuario puede consultar la ficha técnica y atributos PACSS de los jugadores rivales (sin visibilidad de su código fuente de comportamiento)
  6. Al completarse los 4 cuartos, el servidor envía el evento de finalización, actualiza el estado a `FINALIZADO` y cierra la transmisión
* **escenarios excepcionales:**
  * **2a. Pérdida de conexión:** Si la conexión WebSocket se interrumpe, el cliente intenta reconectarse automáticamente al canal del partido

* **CU29:** Realizar sustitución o cambio táctico durante pausa de partido (máx 1 por pausa, máx 3 total)
* **Actor:** Usuario autenticado (propietario de uno de los clubes en juego)
* **Precondición:** El partido está `EN_CURSO` y entra en una de las 3 pausas reglamentarias (mitad del 1° cuarto, entretiempo o mitad del 2° cuarto)
* **escenario exitoso principal:**
  1. El sistema de simulación detiene el avance del cronómetro del partido e inicia la cuenta regresiva de la pausa de n segundos.
  2. El sistema habilita en la vista del partido el panel de control táctico
  3. El usuario realiza una de las siguientes acciones (o ambas):
     * **Sustitución:** Selecciona un jugador titular para salir y un suplente habilitado para ingresar (respetando el límite de 1 sustitución por pausa y máximo 3 en el partido)
     * **Cambio táctico:** Reasigna un script de comportamiento diferente a cualquiera de sus titulares
  4. El usuario presiona "Confirmar Cambios".
  5. El cliente envía el comando táctico al servidor a través del canal **WebSocket** abierto
  6. El servidor valida que no se haya superado el cupo de sustituciones y que la orden haya ingresado dentro del tiempo de la pausa
  7. El servidor aplica los cambios en el motor de simulación y reanuda el siguiente tramo del partido con la nueva alineación.
* **escenarios excepcioanles:**
  * **1a. Solicitud de cambio previa:** Si el usuario planificó un cambio durante el juego activo, el sistema lo aplica de forma automática al comenzar la pausa sin requerir confirmación manual
  * **3a. La pausa concluye sin cambios:** Si el usuario no realiza ninguna acción durante los n segundos, el sistema reanuda el partido con la configuración previa y la oportunidad de cambio de esa pausa se pierde (no es acumulable)
  * **6a. Intento de realizar más de una sustitución en la misma pausa:** El sistema bloquea el segundo cambio e informa que solo se permite una sustitución por pausa

### Módulo: Rankings
* **CU31:** Consultar ranking global de clubes

* **Actor:** Usuario autenticado / Visitante 
* **Precondición:** El usuario accede a la sección de clasificación del sistema
* **escenario exitoso principal:**
  1. El usuario navega al apartado "Ranking Global" desde el menú principal
  2. El sistema consulta la base de datos y recupera la tabla general consolidada de clubes
  3. El sistema aplica el ordenamiento de los clubes según los criterios de puntuación oficiales obtenidos exclusivamente a partir de partidos disputados en **ligas públicas**:
     * **Puntos totales:** Victoria = 3 pts, Empate = 1 pt, Derrota = 0 pts
     * **1° Criterio de desempate:** Mayor Diferencia de Gol {Goles a Favor} - {Goles en Contra}
     * **2° Criterio de desempate:** Mayor cantidad de Goles a Favor
     * **3° Criterio de desempate:** Mayor cantidad de Partidos Ganados
  4. El sistema presenta la tabla de clasificación mostrando para cada club:
     * Posición en el ranking
     * Avatar y nombre del club
     * Puntos acumulados
     * Partidos jugados (PJ), ganados (PG), empatados (PE) y perdidos (PP).
     * Goles a favor (GF), goles en contra (GC) y diferencia de gol (DG).
  5. El usuario puede buscar un club específico por nombre o hacer clic sobre una fila para acceder al perfil público de ese club (CU05)
* **escenarios excepcionales:**
  * **2a. No hay ligas públicas finalizadas aún:** El sistema muestra la tabla inicial con todos los clubes registrados en 0 puntos 