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
* **Escenarios excepcionales:**\
    No aplica.

## Modulo Club

### Caso de uso #: Consultar perfil de club rival
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario selecciona el nombre o avatar de un club rival.
  2. El sistema recupera y muestra la información pública del club:
     * Nombre del club y avatar actual.
     * Estadísticas generales (partidos jugados, victorias, empates, derrotas, posición en el ranking global).
     * Plantilla de jugadores del club con sus respectivos nombres.
* **Escenarios excepcionales:**\
    No aplica.

## Módulo: Gestión de Plantel y Comportamientos

### Caso de uso #: Crear jugador
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario accede a la sección para "Crear Jugador".
  2. El sistema despliega un formulario solicitando:
     * Nombre del jugador
     * Asignación de puntos para cada atributo PACSS: Power, Agility, Control, Speed y Strength
  3. El usuario ingresa el nombre y distribuye los puntos entre los 5 atributos y presiona guardar.
  4. El sistema confirma la creación y actualiza la lista de jugadores disponibles.
* **Escenarios excepcionales:**\
    4. a) La sumatoria de PACSS es distinta de 300\
    El sistema notifica del error en la asignación.\
    4. b) Uno o más atributos estan fuera del rango permitido ($< 20$ o $> 100$)\
    El sistema resalta los campos fuera de rango y exige corregirlos.\
    4. c) El jugador no tiene nombre\
    El sistema solicita completar el campo obligatorio de nombre.

### Caso de uso #: Listar jugadores del club
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario selecciona la opción para ver sus jugadores.
  2. El sistema muestra una vista con la información de cada jugador.
* **Escenarios excepcionales:**\
  2. a) El club no posee jugadores creados.\
  El sistema notifica que no hay jugadores creados.

### Caso de uso #: Eliminar jugador del club 
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario selecciona la opción "Eliminar" en un jugador específico
  2. El sistema solicita confirmación advirtiendo que la acción eliminara al jugador.
  3. El usuario confirma la eliminación
  4. El sistema realiza una baja del jugador 
  5. El sistema confirma la eliminación y refresca el listado del plantel.
* **Escenarios excepcionales:**\
    2. a) El club está jugando un partido\
    El sistema que no se pueden eliminar jugadores mientras se juega un partido.\
    2. b) El jugador esta en una liga que aún no concluye \
    El sistema notifica que no se pueden eliminar jugadores que juegan en una liga.


### Caso de uso #: Crear comportamiento 
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario presiona la opción para crear comportamiento.
  2. El sistema presenta la interfaz con campo para el nombre del comportamiento y entorno de edición.
  3. El usuario ingresa un nombre y diseña la secuencia lógica. Luego guarda el comportamiento.
  4. El sistema guarda el comportamiento.
* **Escenarios Excepcionales:**\
    2. a) El club está jugando un partido\
    El sistema notifica que no se pueden crear comportamientos mientras se juega un partido.\
    4. a) Lo actualizado es invalido\
    El sistema marca los errores lógicos y solicita repararlos antes de guardar.

### Caso de uso #: Editar un comportamiento 
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa y al menos un comportamiento creado.
* **escenario exitoso principal:**
  1. El usuario ingresa al listado de comportamientos y presiona "Editar" sobre uno existente.
  2. El sistema carga en el editor, el nombre y la lógica actual del comportamiento.
  3. El usuario realiza las modificaciones deseadas y las guarda.
  4. El sistema actualiza el comportamiento.
* **escenarios excepcionales:**\
    2. a) El club está jugando un partido\
    El sistema notifica que no se pueden editar comportamientos mientras se juega un partido.\
    4. a) Lo actualizado es invalido\
    El sistema marca los errores lógicos y solicita repararlos antes de realizar cambios.

### Caso de uso #: Eliminar comportamiento 
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario presiona el botón "Eliminar" en un comportamiento especifico.
  2. El sistema solicita confirmación al usuario.
  3. El usuario confirma la eliminación.
  4. El sistema notifica la eliminación exitosa y lo retira del listado activo.
* **Escenarios excepcionales:**\
    2. a) El club está jugando un partido\
    El sistema notifica que no se pueden eliminar comportamientos mientras se juega un partido.

### Caso de uso #: Ver comportamientos del club
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario ingresa a la sección "Comportamientos"
  2. El sistema muestra la lista de tácticas con su nombre, fecha de creación/modificación y las opciones de "Editar", "Ver" o "Eliminar".
* **Escenarios excepcioanles:**\
    2. a) No existen comportamientos registrados\
    El sistema muestra un mensaje indicando que el club aún no posee tácticas creadas.

## Módulo: Ligas y Torneos

### Caso de uso #: Crear liga Pública
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario presiona "Crear liga pública".
  2. El sistema despliega el formulario de configuración solicitando:
     * Nombre de la liga
     * Cantidad mínima de clubes
     * Cantidad máxima de clubes
     * Tiempo de espera entre rondas (Seguidas, Diarias, Semanales).
	     * Diarias: Pedirá hora a jugar. 
	     * Semanales: Pedirá hora y día a jugar.
     * Hora y día de inicio de liga. 
  3. El usuario completa los parámetros y confirma la creación.
  4. El sistema crea la liga y la muestra en la sección "Ligas disponibles".
* **Escenarios excepcionales:**\
  4. a) Existe un campo vacío o inválido \
  El sistema resalta los bloques incompletos ó inválidos.

### Caso de uso #: Crear liga Privada
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario presiona "Crear liga privada".
  2. El sistema despliega el formulario de configuración solicitando:
     * Nombre de la liga
     * Cantidad mínima de clubes
     * Cantidad máxima de clubes
     * Tiempo de espera entre rondas (Seguidas, Diarias, Semanales).
	     * Diarias: Pedirá hora a jugar. 
	     * Semanales: Pedirá hora y día a jugar.
     * Hora y día de inicio de liga. 
  3. El usuario completa los parámetros y confirma la creación.
  4. El sistema crea la liga, le muestra el codigo al creador y la muestra en la sección "Ligas disponibles".
* **Escenarios excepcionales:**\
  4. a) Existe un campo vacío o inválido \
  El sistema resalta los bloques incompletos ó inválidos.


### Caso de uso #: Ver ligas
* **Actor primario:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario abre "Explorar Ligas"
  2. El sistema presenta la lista de ligas públicas con cupos disponibles.
* **Escenarios excepcionales:**\
    2. a) No hay ligas disponibles con cupo abierto\
    El sistema muestra un mensaje indicando que no se encontraron ligas abiertas.

### Caso de uso #: Buscar entre las ligas disponibles
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa y hay ligas disponibles.
* **Escenario exitoso principal:**
  1. El usuario filtra ligas disponibles por nombre.
  2. El sistema presenta la lista de ligas públicas con cupos disponibles que coinciden con lo filtrado.
* **Escenarios excepcionales:**\
    2. a) No hay ligas disponibles con cupo abierto que coincidan con lo filtrado.\
    El sistema muestra un mensaje indicando que no se encontraron coincidencias.

### Caso de uso #: Inscribirse a una liga Pública
* **Actor primario:** Usuario
* **Precondición:** El usuario tiene una sesión activa. La liga esta disponible y no ha alcanzado el cupo máximo.
* **Escenario exitoso principal:**
  1. El usuario selecciona una liga y presiona "Unirse"
  2. El sistema muestra como quedaría su equipo default y consulta si desea confirmar.
  3. El usuario confirma la inscripción.
  4. El sistema notifica que se ha unido a una liga.
* **Escenarios excepcionales:**\
  4. a) La liga llena simultáneamente pues otro club ocupó el último cupo instantes antes. \
  El sistema notifica que la liga se ha completado y no ha podido inscribirse.

### Caso de uso #: Inscribirse a una liga Privada
* **Actor primario:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa. La liga esta disponible y no ha alcanzado el cupo máximo.
* **Escenario exitoso principal:**
  1. El usuario selecciona una liga y presiona "Unirse".
  2. El sistema solicita ingresar el código de acceso. 
  3. El usuario ingresa el codigo de acceso.
  4. El sistema muestra como quedaría su equipo default y consulta si desea confirmar.
  5. El usuario confirma la inscripción.
  6. El sistema notifica que se ha unido a una liga.
* **Escenarios excepcionales:**\
  4. a) El codigo de acceso es incorrecto\
  El sistema notifica que no ha podido inscribirse.\
  6. a) La liga llena simultáneamente pues otro club ocupó el último cupo instantes antes. \
  El sistema notifica que la liga se ha completado y no ha podido inscribirse.

### Caso de uso #: Abandonar liga
* **Actor primario:** Usuario
* **Precondición:** El club está inscripto en una liga que no ha sido iniciada.
* **escenario exitoso principal:**
  1. El usuario selecciona la opción "Abandonar Liga"
  2. El sistema solicita confirmación de la baja.
  3. El usuario confirma la acción.
  4. El sistema confirma la desvinculación y redirige al usuario a su panel principal.
* **Escenarios excepcionales:** \
    No aplica.

### Caso de uso #: Iniciar liga
* **Actor primario:** Usuario
* **Precondición:** La liga está disponible y la cantidad de clubes inscriptos es mayor o igual a la cantidad mínima configurada.
* **Escenario exitoso principal:**
  1. El creador presiona "Iniciar Liga".
  2. El sistema inicia la liga. Muestra el fixture y la tabla de puntaje en 0. \
  Ademas avisa cuando será el primer partido. 
* **Escenarios excepcionales:** \
    No aplica.

### Caso de uso #: Cancelar liga
* **Actor primario:** Usuario
* **Precondición:** La liga aún no ha iniciado
* **escenario exitoso principal:**
  1. El creador presiona "Cancelar Liga".
  2. El sistema muestra una advertencia indicando que la liga será cancelada y se removerán todos los clubes inscriptos.
  3. El creador confirma la cancelación.
  4. El sistema notifica la cancelación y redirige al creador a su panel.
* **escenarios excepcionales:**
    No aplica.

### Caso de uso #: Consultar fixture, rondas y tabla de posiciones de una liga
* **Actor primario:** Usuario autenticado perteneciente a la liga.
* **Precondición:** El club del usuario se encuentra inscripto en una liga que ha sido iniciada.
* **Escenario exitoso principal:**
    1. El usuario accede al detalle de la liga.
    2. El sistema muestra el fixture completo de la liga organizado por rondas. \
    El sistema muestra la tabla de posiciones de la liga.
* **Escenarios excepcionales:**\
    No aplica

### Caso de uso #: Configurar alineación previa al partido 
* **Actor primario:** Usuario.
* **Precondición:** El club tiene un partido programado (de liga o amistoso) que aún no ha comenzado.
* **Escenario exitoso:**
  1. El usuario accede al detalle de su próximo partido.
  2. El sistema carga la alineación por defecto del club (los 6 jugadores inscriptos en la liga con sus comportamientos y la formación).
  3. El usuario hace cambios previos y presiona "Guardar Alineación".
  4. El sistema guarda la configuración táctica específica para el encuentro.
* **Escenarios excepcionales:**\
  4. a) Quedo algun campo incompleto.\
  El sistema solicita completar el campo obligatorio.

### Caso de uso #: Observar partido en vivo
* **Actor primario:** Usuario
* **Precondición:** El club del usuario pertenece a la misma liga del partido que desea observar y el partido se encuentra en curso.
* **Escenario exitoso principal:**
  1. El usuario accede al fixture de la liga.
  2. El sistema muestra los partidos que se encuentran en curso.
  3. El usuario selecciona el partido que desea observar.
  4. El sistema muestra la representación en vivo del partido, incluyendo: clubes participantes, jugadores en cancha, marcador, tiempo restante, etapa actual del partido.\
  Durante las pausas de hidratación y el entretiempo, el sistema informa que el partido se encuentra temporalmente pausado.
  Al finalizar el partido, el sistema muestra el resultado definitivo.
* **Escenarios excepcionales:**
    No aplica.

### Caso de uso #: Planear cambio de jugador
* **Actor primario:** Usuario
* **Precondición:** El partido está en curso.
* **Escenario exitoso principal:**
  1.  El usuario aprieta "Planificar cambio" durante el tiempo de juego.
  2. El sistema habilita en la vista el panel de control táctico. 
  3. El usuario selecciona el jugador que desea cambiar. 
  4. El sistema muestra los jugadores disponibles para dicho reemplazo. 
  5. El usuario decide cuál quiere y presiona "confirmar cambios".
  6. El sistema refleja los cambios en el partido luego de la siguiente pausa, ya sea de hidratación o entretiempo.
* **Escenarios excepcionales:**\
	2. a) Se intenta realizar más de una sustitución en la misma pausa. \
  El sistema bloquea el segundo cambio e informa que solo se permite una sustitución por pausa.

### Caso de uso #: Realizar cambio en pausa
* **Actor primario:** Usuario
* **Precondición:** El partido está en curso y está en una de las 3 pausas reglamentarias (hidratación 1, entretiempo, hidratación 2)
* **Escenario exitoso principal:**
  1. El usuario toca "Realizar cambio".
  2. El sistema pide seleccionar el jugador a cambiar.
  3. El usuario selecciona el jugador que desea cambiar. 
  4. El sistema muestra los jugadores disponibles para dicho reemplazo. 
  5. El usuario decide cuál quiere y presiona "confirmar cambios".
  6. El sistema al finalizar la pausa refleja el cambio hecho. 
* **Escenario excepcional:**
	2. a) Se intenta realizar más de una sustitución en la misma pausa. \
  El sistema bloquea el segundo cambio e informa que solo se permite una sustitución por pausa.

### Caso de uso #: Anular planeamiento de cambio
* **Actor primario:** Usuario
* **Precondición:** El partido está en curso y hay cambios planificados.
* **Escenario exitoso principal:**
  1. El usuario toca "Realizar cambio".
  2. El sistema habilita en la vista el panel de control táctico. 
  3. El usuario selecciona "Anular cambio".
  4. El sistema no aplica el cambio en tiempo de pausa. 
* **Escenarios excepcionales:** \
    No aplica.

### Módulo: Rankings
### Caso de uso 32: Consultar ranking global de clubes
* **Actor primario:** Usuario 
* **Precondición:** El usuario posee una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario navega al apartado "Ranking Global" desde el menú principal
  2. El sistema aplica el ordenamiento de los clubes según los criterios de puntuación oficiales y presenta la tabla de clasificación mostrando para cada club:
     * Posición en el ranking
     * Avatar y nombre del club
     * Puntos acumulados
     * Partidos jugados (PJ), ganados (PG), empatados (PE) y perdidos (PP).
     * Goles a favor (GF), goles en contra (GC) y diferencia de gol (DG).
* **Escenarios excepcionales:**\
    No aplica.