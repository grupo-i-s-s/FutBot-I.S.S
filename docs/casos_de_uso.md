# Casos de Uso - FutBot
 **Versión:** 0.4

## Módulo: Autenticación y Cuenta

### Caso de uso #: Registrar nuevo usuario
* **Actor primario:** Usuario
* **Precondición:** El usuario no se ha registrado en el sistema. 
* **Escenario exitoso Principal:**
  1. El visitante accede a la vista de registro.
  2. El sistema muestra un formulario a completar para registrar el nuevo usuario.
  3. El usuario completa los datos requeridos.
  4. El sistema guarda el formulario de registro que contiene nombre, nombre de usuario, correo electrónico, nombre del club, avatar y contraseña y notifica que se ha creado la cuenta.
* **Casos excepcionales:** \
  4. a) El email o el nombre de usuario ya estan registrados  en otro usuario\
  El sistema notifica que el correo o nombre de usuario ya están en uso.\
  4. b) Existen campos obligatorios vacíos o inválidos\
  El sistema resalta los campos con error.

### Caso de uso #: Iniciar sesión 
* **Actor primario:** Usuario 
* **Precondición:** El usuario posee una cuenta registrada en el sistema y no tiene una sesión activa en el cliente.
* **Escenario exitoso principal:**
  1. El usuario accede a la pantalla de inicio de sesión.
  2. El sistema solicita nombre usuario y contraseña.
  3. El usuario ingresa sus datos y presiona "Iniciar Sesión".
  4. Se redirige al usuario a la vista principal de su club.
* **Escenarios excepcionales:** \
    4. a) Las credenciales ingresadas son inválidas \
    El sistema muestra un mensaje de error.\
    4. b) La cuenta ingresada es inexistente \
	  El sistema muestra el mismo mensaje de error que en 4a.

### Caso de uso #: Cerrar sesión 
* **Actor primario:** Usuario
* **Precondición:** El usuario cuenta con una sesión activa en la aplicación.
* **Escenario exitoso principal :**
  1. El usuario presiona el botón "Cerrar Sesión".
  2. El sistema dirige al usuario a la página de inicio.
* **Escenarios excepcionales:**
    No aplica.

## Modulo Club

### Caso de uso #: Consultar perfil de club rival
* **Actor primario:** Usuario.
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario selecciona el nombre o avatar de un club rival.
  2. El sistema recupera y muestra la información pública del club:
     * Nombre del club y avatar actual.
     * Estadísticas generales (partidos jugados, victorias, empates, derrotas, posición en el ranking global).
     * Plantilla de jugadores del club con sus respectivos nombres.
  3. El usuario visualiza la ficha técnica del rival sin acceso a su código fuente ni tácticas privadas.
* **Escenarios excepcionales:**
  * **2a. Finaliza el partido:** El sistema no muestra información sobre el rival y redirige al inicio. 

## Módulo: Gestión de Plantel y Comportamientos

### Caso de uso 10: Crear jugador
* **Actor primario:** Usuario autenticado.
* **Precondición:** El usuario tiene una sesión activa.
* **escenario exitoso principal:**
  1. El usuario accede a la sección para "Crear Jugador".
  2. El sistema despliega un formulario solicitando:
     * Nombre del jugador
     * Asignación de puntos para cada atributo PACSS: Power, Agility, Control, Speed y Strength
  3. El usuario ingresa el nombre y distribuye los puntos entre los 5 atributos y presiona guardar.
  4. El sistema confirma la creación y actualiza la lista de jugadores disponibles.
* **escenarios excepcionales:**
    4. a) La sumatoria de PACSS distinta de 300
    El sistema indica visualmente la cantidad de puntos sobrantes o faltantes para alcanzar exactamente los puntos requeridos.
    4. b) Uno o más atributos estan fuera del rango permitido ($< 20$ o $> 100$)
    El sistema resalta los campos fuera de rango y exige corregirlos antes de continuar.
    4. c) El jugador no tiene nombre
    El sistema solicita completar el campo obligatorio del nombre.


### CU11: Listar jugadores del club

* **Actor:** Usuario autenticado.
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario navega al apartado de plantel.
  2. El sistema consulta la base de datos y recupera todos los jugadores activos (no eliminados) pertenecientes al club del usuario.
  3. El sistema muestra una vista con las tarjetas o tabla de cada jugador, mostrando:
     * Nombre del jugador.
     * Desglose de sus 5 atributos PACSS: Power, Agility, Control, Speed, Strength.
* **Escenarios excepcionales:**
  * **2a. El club no posee jugadores creados:** El sistema muestra una vista de los jugadores default brindados por el sistema y un botón de acceso directo a "Crear Jugador"

### Caso de uso 12: Eliminar jugador del club 
* **Actor primario:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa.
* **escenario exitoso principal:**
  1. El usuario selecciona la opción "Eliminar" en un jugador específico
  2. El sistema solicita confirmación advirtiendo que la acción eliminara al jugador.
  3. El usuario confirma la eliminación
  4. El sistema realiza una baja del jugador 
  5. El sistema confirma la eliminación y refresca el listado del plantel.
* **escenarios excepcionales:**
    2. a) El club está jugando un partido
    El sistema bloquea la operación y notifica: *"No se pueden eliminar jugadores mientras se juega un partido"*.
    4. a) El jugador esta en una liga que aún no concluye
    El sistema bloquea la operación y notifica: *"No se pueden eliminar jugadores que juegan en una liga"*.


### CU13: Crear comportamiento 

* **Actor:** Usuario autenticado.
* **Precondición:** El usuario tiene una sesión activa.
* **escenario exitoso principal:**
  1. El usuario accede a la sección "Comportamientos" y presiona "Nuevo Comportamiento"
  2. El sistema comprueba que el club **no tenga partidos en curso**.
  3. El sistema presenta la interfaz con:
     * Campo para el nombre del comportamiento.
     * Entorno de edición lógica.
  4. El usuario ingresa un nombre y diseña la secuencia lógica.
  5. El usuario presiona "Guardar Comportamiento".
  6. El sistema valida que el nombre no esté vacío y sea único, compila/valida la estructura lógica.
  7. El sistema almacena el nuevo `Comportamiento` asociado al club.
  8. El sistema notifica el guardado exitoso y añade el script al listado de tácticas disponibles.
* **Escenarios excepcional:**
  * **2a. Club con partido en curso:** El sistema bloquea el acceso a la creación de comportamientos hasta que finalice el encuentro.
  * **6a. Estructura de bloques incompleta o errónea:** El sistema resalta los bloques desconectados o inválidos e impide el guardado hasta su corrección.

### Caso de uso 14: Editar un comportamiento 
* **Actor primario:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa y al menos un comportamiento creado.
* **escenario exitoso principal:**
  1. El usuario ingresa al listado de comportamientos y presiona "Editar" sobre uno existente.
  2. El sistema carga en el editor de bloques el nombre y la lógica actual del comportamiento.
  3. El usuario realiza las modificaciones deseadas y las guarda.
  4. El sistema valida la consistencia de lo modificado y luego actualiza el comportamiento.
* **escenarios excepcionales:**
    2. a) El club está jugando un partido
    El sistema bloquea la operación y notifica: *"No se pueden editar comportamientos mientras se juega un partido"*.
    4. a) Lo actualizado es invalido
    El sistema marca los errores lógicos y solicita repararlos antes de realizar cambios.

### CU15: Eliminar comportamiento 

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa y visualiza sus comportamientos.
* **Escenario exitoso principal:**
  1. El usuario presiona el botón "Eliminar" en un comportamiento especifico.
  2. El sistema comprueba que el club **no tenga partidos en curso**.
  3. El sistema solicita confirmación al usuario para proceder con el borrado.
  4. El usuario confirma la eliminación.
  5. El sistema ejecuta una baja del comportamiento.
  6. El sistema notifica la eliminación exitosa y lo retira del listado activo.
* **Escenarios excepcionales:**
  * **2a. Club con partido en curso:** El sistema bloquea la eliminación notificando la restricción de partidos activos.
  * **4a. Cancelación:** El usuario cancela y el comportamiento permanece activo.

### Caso de uso 16: Listar comportamientos del club
* **Actor primario:** Usuario autenticado.
* **Precondición:** El usuario ha iniciado sesión
* **escenario exitoso principal:**
  1. El usuario ingresa a la sección "Comportamientos"
  2. El sistema muestra la lista de tácticas con su nombre, fecha de creación/modificación y las opciones de "Editar", "Ver" o "Eliminar".
* **escenarios excepcioanles:**
    2. a) No existen comportamientos registrados
    El sistema muestra un mensaje indicando que el club aún no posee tácticas creadas.

## Módulo: Ligas y Torneos

### CU17.01: Crear liga Pública
* **Actor:** Usuario autenticado (Club Creador).
* **Precondición:** El usuario ha iniciado sesión.
* **Escenario exitoso principal:**
  1. El usuario accede a la sección "Ligas" y luego a "Crear nueva liga pública".
  2. El sistema despliega el formulario de configuración solicitando:
     * Nombre de la liga.
     * Cantidad mínima de clubes (por defecto 3, configurable a un valor mayor o igual a 3)
     * Cantidad máxima de clubes.
     * Tiempo de espera entre rondas (Seguidas, Diarias, Semanales).
	     * Diarias: Pedirá hora a jugar. 
	     * Semanales: Pedirá hora y día a jugar.
     * Hora y día de inicio de liga. 
  3. El usuario completa los parámetros y confirma la creación.
  4. El sistema valida las reglas de negocio:
     * Ningún campo esté vacío.
     * La cantidad mínima es 3.
     * La cantidad máxima es mayor o igual a la mínima.
  5. El sistema crea la `Liga` asignando al club del usuario como creador y la muestra en la sección "Ligas disponibles".
  6. El sistema inscribe automáticamente al club creador como primer participante (completando los datos de inscripción del CU19).
  * **Escenarios excepcionales:**
  * **4a. Campo vacío/inválido:** El sistema resalta los bloques incompletos ó inválidos e impide el guardado hasta su corrección.
  * **4b. Mínimo de clubes menor a 3:** El sistema advierte que el cupo mínimo permitido es de 3 clubes e impide guardar.
  * **4c. Máximo menor al mínimo:** El sistema notifica la inconsistencia en los cupos y solicita corregir los valores.

### CU17.02: Crear liga Privada

* **Actor:** Usuario autenticado (Club Creador).
* **Precondición:** El usuario ha iniciado sesión
* **escenario exitoso principal:**
  1. El usuario accede a la sección "Ligas" y luego a "Crear nueva liga privada".
  2. El sistema despliega el formulario de configuración solicitando:
     * Nombre de la liga.
     * Cantidad mínima de clubes (por defecto 3, configurable a un valor mayor o igual a 3)
     * Cantidad máxima de clubes.
     * Tiempo de espera entre rondas (Seguidas, Diarias, Semanales).
	     * Diarias: Pedirá hora a jugar. 
	     * Semanales: Pedirá hora y día a jugar.
     * Hora y día de inicio de liga. 
  3. El usuario completa los parámetros y confirma la creación.
  4. El sistema valida las reglas de negocio:
     * Ningún campo esté vacío.
     * La cantidad mínima es 3.
     * La cantidad máxima es mayor o igual a la mínima.
  5. El sistema genera un código de ingreso a la liga y muestra la liga en la sección "Ligas Disponibles Privadas".
  6. El sistema inscribe automáticamente al club creador como primer participante (completando los datos de inscripción del CU19).
  * **Escenarios excepcionales:**
  * **4a. Campo vacío/inválido:** El sistema resalta los bloques incompletos ó inválidos e impide el guardado hasta su corrección.
  * **4b. Mínimo de clubes menor a 3:** El sistema advierte que el cupo mínimo permitido es de 3 clubes e impide guardar.
  * **4c. Máximo menor al mínimo:** El sistema notifica la inconsistencia en los cupos y solicita corregir los valores.


### Caso de uso 18.01: Listar ligas disponibles
* **Actor primario:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa.
* **escenario exitoso principal:**
  1. El usuario abre "Explorar Ligas"
  2. El sistema presenta la lista de ligas públicas con cupos disponibles.
* **escenarios excepcionales:**
    2. a) No hay ligas disponibles con cupo abierto
    El sistema muestra un mensaje indicando que no se encontraron ligas abiertas.

### Caso de uso 18.01: Buscar entre las ligas disponibles
* **Actor primario:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa y hay ligas disponibles.
* **escenario exitoso principal:**
  1. El usuario filtra ligas disponibles por nombre.
  2. El sistema presenta la lista de ligas públicas con cupos disponibles que coinciden con lo filtrado.
* **escenarios excepcionales:**
    2. a) No hay ligas disponibles con cupo abierto que coincidan con lo filtrado.
    El sistema muestra un mensaje indicando que no se encontraron coincidencias.

### CU19.01: Inscribirse a una liga Pública

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa. La liga esta disponible y no ha alcanzado el cupo máximo.
* **Escenario exitoso principal:**
  1. El usuario selecciona una liga y presiona "Unirse"
  2. El sistema valida que el club no esté previamente inscripto.
  3. El sistema configura la participación del club en la liga con su equipo default.
  4. El sistema muestra como quedaría y consulta si desea confirmar.
  5. El usuario confirma la inscripción.
  6. El sistema registra la participación del club en la liga. 
  7. Si con esta inscripción se alcanza el cupo máximo de clubes, el sistema bloquea nuevas uniones y deja la liga a la espera de ser iniciada.
* **escenarios excepcionales:**
  * **9a. Liga llena simultáneamente:** Si otro club ocupó el último cupo instantes antes, el sistema notifica que la liga se ha completado.

### CU19.02: Inscribirse a una liga Privada

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa. La liga esta disponible y no ha alcanzado el cupo máximo.
* **Escenario exitoso principal:**
  1. El usuario selecciona una liga y presiona "Unirse".
  2. 5. El sistema valida que el club no esté previamente inscripto..
  3. El sistema solicita ingresar el código de acceso. 
  4. El usuario lo ingresa.
  5. El sistema valida que coincida.
  6. El sistema configura la participación del club en la liga con su equipo default.
  7. El sistema muestra como quedaría y consulta si desea confirmar.
  8. El usuario confirma la inscripción.
  9. El sistema registra la participación del club en la liga. 
  10. Si con esta inscripción se alcanza el cupo máximo de clubes, el sistema bloquea nuevas uniones y deja la liga a la espera de ser iniciada.
* **escenarios excepcionales:**
  * **5a. Código de acceso incorrecto:** El sistema deniega el acceso e informa el error.
  * **10a. Liga llena simultáneamente:** Si otro club ocupó el último cupo instantes antes, el sistema notifica que la liga se ha completado


### Caso de uso 20: Abandonar liga
* **Actor primario:** Usuario autenticado
* **Precondición:** El club está inscripto en una liga que no ha sido iniciada.
* **escenario exitoso principal:**
  1. El usuario selecciona la opción "Abandonar Liga"
  2. El sistema solicita confirmación de la baja.
  3. El usuario confirma la acción.
  4. El sistema confirma la desvinculación y redirige al usuario a su panel principal.
* **escenarios excepcionales:**
    No aplica.

### CU21: Iniciar liga (Creador, con cupo mínimo alcanzado)

* **Actor:** Usuario autenticado (Club Creador).
* **Precondición:** La liga está disponible y la cantidad de clubes inscriptos es mayor o igual a la cantidad mínima configurada.
* **Escenario exitoso principal:**
  1. El creador presiona "Iniciar Liga".
  2. El sistema inicia la liga y la oculta en la sección de "Ligas disponibles".
  3. El sistema genera automáticamente el `Fixture` con el calendario completo de partidos en formato todos contra todos, agrupándolos por rondas.
  4. El sistema inicializa la `TablaDePuntaje` con todos los clubes inscriptos en 0 puntos.
  5. El sistema notifica a todos los participantes e inicia la cuenta regresiva para la primera ronda de partidos simultáneos.
* **escenarios excepcionales:**
  * **2a. No se alcanza el cupo mínimo de clubes:** El botón permanece deshabilitado informando cuántos clubes faltan para poder arrancar.

### Caso de uso 22: Cancelar liga
* **Actor primario:** Usuario autenticado
* **Precondición:** La liga aún no ha iniciado
* **escenario exitoso principal:**
  1. El creador presiona "Cancelar Liga".
  2. El sistema muestra una advertencia indicando que la liga será cancelada y se removerán todos los clubes inscriptos.
  3. El creador confirma la cancelación.
  4. El sistema notifica la cancelación y redirige al creador a su panel.
* **escenarios excepcionales:**
    No aplica.


### CU23: Consultar fixture, rondas y tabla de posiciones de una liga

- **Actor:** Usuario autenticado perteneciente a la liga.
- **Precondición:** El club del usuario se encuentra inscripto en una liga que ha sido iniciada.
- **Escenario exitoso principal:**
    1. El usuario accede al detalle de la liga.
    2. El sistema muestra el fixture completo de la liga organizado por rondas.
    3. Para cada ronda, el sistema muestra:
        - Los clubes enfrentados.
        - El horario de cada partido.
        - El estado del partido: programado, en curso o finalizado.
        - El resultado, en caso de que el partido haya finalizado.
    4. El sistema muestra la tabla de posiciones de la liga.
    5. Los clubes se ordenan de acuerdo con los puntos obtenidos:
        - Partido ganado: 3 puntos.
        - Partido empatado: 1 punto.
        - Partido perdido: 0 puntos.
    6. En caso de empate en puntos, el sistema aplica los criterios de desempate establecidos:
        1. Mayor diferencia de goles.
        2. Mayor cantidad de goles a favor.
        3. Menor cantidad de goles en contra.
    7. El usuario puede seleccionar una ronda para consultar sus partidos.
    8. Si uno de los partidos de la liga se encuentra en curso, el usuario puede seleccionarlo para observarlo en vivo.
- **Escenarios excepcionales:**
    - **3a. Ronda aún no disputada:** El sistema muestra los enfrentamientos y horarios programados sin resultados.
    - **8a. Partido no iniciado** Si el usuario intenta acceder a un partido no iniciado, el sistema muestra la cancha vacía. 
    - **8b. Partido finalizado:** Si el usuario intenta acceder a un partido que acaba de finalizar, el sistema muestra su resultado final.

### Caso de uso 24:ELIMINADO
---

## Módulo: Partidos y Simulación        (asumiendo que existe el sistema de amigos)
### CU25:ELIMINADO

### CU26:ELIMINADO

### CU27: Configurar alineación previa al partido (titulares, suplentes y formación)

* **Actor:** Usuario autenticado.
* **Precondición:** El club tiene un partido programado (de liga o amistoso) que aún no ha comenzado.
* **Escenario exitoso:**
  1. El usuario accede al detalle de su próximo partido.
  2. El sistema carga la alineación por defecto del club (los 6 jugadores inscriptos en la liga con sus comportamientos y la formación).
  3. El usuario hace cambios previos:
     * Intercambia qué jugadores arrancan como titulares y cuáles como suplentes
     * Selecciona la formación táctica.
     * Modifica los scripts de comportamiento asignados a cada titular
  4. El usuario presiona "Guardar Alineación".
  5. El sistema valida que haya exactamente 3 titulares y 3 suplentes, que cada titular tenga un comportamiento asignado y haya una formación definida.
  6. El sistema guarda la configuración táctica específica para el encuentro.
* **Escenarios excepcioanles:**
  * **5a. Campos incompletos:** Quedó algún camop jugador, comportamiento o formación incompleto, el sistema lo marca y pide que lo complete.

### Caso de uso 28: Observar partido en vivo
* **Actor primario:** Usuario autenticado perteneciente a la liga.
* **Precondición:** El club del usuario pertenece a la misma liga del partido que desea observar y el partido se encuentra en curso.
* **Escenario exitoso principal:**
  1. El usuario accede al fixture de la liga.
  2. El sistema identifica los partidos que se encuentran en curso.
  3. El usuario selecciona el partido que desea observar.
  4. El sistema muestra la representación en vivo del partido, incluyendo:
      - Clubes participantes.
      - Jugadores en cancha.
      - Marcador.
      - Tiempo restante.
      - Etapa actual del partido.
  Durante las pausas de hidratación y el entretiempo, el sistema informa que el partido se encuentra temporalmente pausado.
  Al finalizar el partido, el sistema muestra el resultado definitivo.
* **Escenarios excepcionales:**
    No aplica.

### CU29: Planear cambio de jugador

* **Actor:** Usuario autenticado (propietario de uno de los clubes en juego)
* **Precondición:** El partido está en curso.
* **Escenario exitoso principal:**
1.  El usuario aprieta "Planificar cambio" durante el tiempo de juego.
2. El sistema habilita en la vista el panel de control táctico. 
3. El usuario selecciona el jugador que desea cambiar. 
4. El sistema muestra los jugadores disponibles para dicho reemplazo. 
5. El usuario decide cuál quiere y presiona "confirmar cambios".
6. El sistema refleja los cambios en el partido luego de la siguiente pausa, ya sea de hidratación o entretiempo.
* **Escenarios excepcional:**
  * **6a. La pausa concluye sin cambios:** Si el usuario no realiza ninguna acción durante los n segundos, el sistema reanuda el partido con la configuración previa y la oportunidad de cambio de esa pausa se pierde (no es acumulable).
  * **6b. Intento de realizar más de una sustitución en la misma pausa:** El sistema bloquea el segundo cambio e informa que solo se permite una sustitución por pausa

### Caso de uso 30: Realizar cambio en pausa
* **Actor primario:** Usuario autenticado (propietario de uno de los clubes en juego)
* **Precondición:** El partido está en curso y está en una de las 3 pausas reglamentarias (hidratación 1, entretiempo, hidratación 2)
* **Escenario exitoso principal:**
  1. El usuario toca "Realizar cambio".
  2. El sistema pide seleccionar el jugador a cambiar.
  3. El usuario selecciona el jugador que desea cambiar. 
  4. El sistema muestra los jugadores disponibles para dicho reemplazo. 
  5. El usuario decide cuál quiere y presiona "confirmar cambios".
  6. El sistema al finalizar la pausa refleja el cambio hecho. 
* **Escenario excepcional:**
	2. a) Se intenta realizar más de una sustitución en la misma pausa
  El sistema bloquea el segundo cambio e informa que solo se permite una sustitución por pausa.

### CU31: Anular planeamiento de cambio

* **Actor:** Usuario autenticado (propietario de uno de los clubes en juego)
* **Precondición:** El partido está en curso y hay cambios planificados.
* **Escenario exitoso principal:**
 1. El usuario toca "Realizar cambio".
 2. El sistema habilita en la vista el panel de control táctico. 
 3. El usuario selecciona "Anular cambio".
 4. El sistema descarta el cambio planeado y no lo aplica en el tiempo de pausa. 
 - **Escenario excepcional:** 
	 -  No aplica.

### Módulo: Rankings
### Caso de uso 32: Consultar ranking global de clubes
* **Actor primario:** Usuario autenticado
* **Precondición:** El usuario accede a la sección de clasificación del sistema
* **escenario exitoso principal:**
  1. El usuario navega al apartado "Ranking Global" desde el menú principal
  2. El sistema aplica el ordenamiento de los clubes según los criterios de puntuación oficiales y presenta la tabla de clasificación mostrando para cada club:
     * Posición en el ranking
     * Avatar y nombre del club
     * Puntos acumulados
     * Partidos jugados (PJ), ganados (PG), empatados (PE) y perdidos (PP).
     * Goles a favor (GF), goles en contra (GC) y diferencia de gol (DG).
  3. El usuario puede buscar un club específico por nombre o hacer clic sobre una fila para acceder al perfil público de ese club (CU05)
* **escenarios excepcionales:**
    No aplica.