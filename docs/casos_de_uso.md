# Casos de Uso - FutBot
 **Versión:** 0.1

## Módulo: Autenticación y Cuenta
### CU01: Registrar nuevo usuario

* **Actor:** Visitante
* **Precondición:** El visitante no se ha registrado en el sistema. 
* **Escenario exitoso Principal:**
  1. El visitante accede a la vista de registro.
  2. El sistema presenta el formulario de registro solicitando: nombre completo, nombre de usuario (`username`), correo electrónico (`email`), contraseña (`password`).
  3. El visitante completa los campos y envía el formulario.
  4. El sistema valida los datos:
     * El formato del correo electrónico es válido y no está registrado previamente.
     * El nombre de usuario es único.
  5. El sistema crea la cuenta del `Usuario`.
  6. El sistema crea automáticamente la entidad `Club` asociada al nuevo usuario. *Deberá Configurarlo: CU01.1*.
* **Casos excepcionales:**
  * **4a. Datos duplicados (Email o Username ya existentes):** El sistema notifica que el correo o nombre de usuario ya están en uso y solicita ingresar valores diferentes
  * **4c. Campos obligatorios vacíos o inválidos:** El sistema resalta los campos con error y vuelve a pedir que ingrese los datos.
### CU01.1: Configurar club

- **Actor**: Usuario.
- **Precondición**: El usuario ya completó datos de registro. 
- **Escenario exitoso principal:**
    1. El usuario debe configurar su club. 
    2. El sistema presenta un formulario solicitando:
        - Nombre del club.
        - Avatar, seleccionado desde la biblioteca de avatares brindada por el sistema.
    3. El usuario ingresa el nombre de su club y selecciona un avatar.
    4. El usuario confirma la configuración.
    5. El sistema valida que los campos obligatorios hayan sido completados.
    6. El sistema configura el club asociado al usuario con el nombre y avatar seleccionados.
    7. El sistema le asigna al club un equipo default de 3 jugadores titulares, 3 suplentes y un comportamiento para todos. 
    8. El sistema confirma la configuración y permite al usuario acceder al panel principal de su club.
    9. El usuario pone "Continuar".
    10. El sistema redirige al inicio de FutBot. 
- **Casos excepcionales:**
	 **5a. Campos obligatorios incompletos:** El sistema informa al usuario qué campos deben completarse antes de continuar.

#### CU02: Iniciar sesión 

* **Actor:** Usuario registrado.
* **Precondición:** El usuario posee una cuenta registrada en el sistema.
* **Escenario exitoso principal:**
  1. El usuario accede a la pantalla de inicio de sesión.
  2. El sistema solicita: correo electrónico (`email`) y contraseña (`password`).
  3. El usuario ingresa sus datos y presiona "Iniciar Sesión".
  4. El sistema valida que el correo exista y que el hash de la contraseña coincida con el registrado en la base de datos.
  5. El sistema redirige al usuario a la vista principal de su club.
* **escenarios excepcionales:**
  * **4a. Credenciales inválidas:** El sistema muestra un mensaje de error genérico (*"Correo o contraseña incorrectos"*) por motivos de seguridad y permite reintentar el ingreso.
  * **4b. Cuenta inexistente:** Si el correo no figura en el sistema, se muestra el mismo mensaje de error genérico que en 4a

### CU03: Modificar club

- **Actor:** Usuario autenticado.
- **Precondición:** El usuario se ha registrado correctamente en el sistema.
- **Escenario exitoso principal:**
    1. El usuario accede a la configuración de su club.
    2. El sistema muestra el avatar actual y la biblioteca de avatares disponibles.
    3. El usuario selecciona un nuevo avatar.
    4. El usuario confirma el cambio.
    5. El sistema actualiza el avatar del club.
    6. El sistema refleja el nuevo avatar en la interfaz y confirma que el cambio fue realizado correctamente.
- **Escenarios excepcionales:**
    - **4a. Cancelación de modificación:** Si el usuario cancela la modificación del avatar, el sistema conserva el avatar anterior sin realizar cambios.

* **CU04:** Cerrar sesión 
* **Actor:** Usuario autenticado
* **Precondición:** El usuario cuenta con una sesión activa en la aplicación
* **escenario exitoso principal :**
  1. El usuario presiona el botón "Cerrar Sesión" desde el menú de navegación o perfil
  2. El sistema invalida la sesión activa.
  3. El sistema redirige al usuario a la página de inicio/login para visitantes
* **escenarios excepcionales:**
  * No presenta(el cierre de sesión local es inmediato)

### **CU05:** Consultar perfil de club rival

* **Actor:** Usuario autenticado.
* **Precondición:** El usuario tiene una sesión activa y visualiza un listado público.
* **Escenario exitoso principal:**
  1. El usuario selecciona el nombre o avatar de un club rival.
  2. El sistema recupera y muestra la información pública del club:
     * Nombre del club y avatar actual.
     * Estadísticas generales (partidos jugados, victorias, empates, derrotas, posición en el ranking global).
     * Plantilla de jugadores del club con sus respectivos nombres.
  3. El usuario visualiza la ficha técnica del rival sin acceso a su código fuente ni tácticas privadas.
* **Escenarios excepcionales:**
  * **2a. Finaliza el partido:** El sistema no muestra información sobre el rival y redirige al inicio. 

### Módulo: Sistema de Amigos 
* **CU06:** Buscar usuario por username
* **Actor:** Usuario autenticado 
* **Precondición:** El usuario ha iniciado sesión y administra su club
* **Escenario exitoso principal:** 
	1. El usuario accede a la sección "Amigos".
	2. El usuario ingresa el username del usuario que desea buscar. 
	3. EL sistema busca el usuario cuyo username coincida con el ingresado.
	4. El sistema muestra el usuario encontrado junto con la información pública necesaria para identificarlo. 
	5. El usuario puede seleccionar al usuario encontrado para enviarle una solicitud de amistad. 
- **Escenarios excepcionales:**
	- 2a.  Búsqueda vacía:** El sistema solicita ingresar un `username` antes de realizar la búsqueda.
	- 3a. Usuario no encontrado:** El sistema informa que no existe ningún usuario con el `username` ingresado.

#  CU07 ELIMINADO


* **CU08:** Aceptar / Rechazar solicitud de amistad
* **Actor:** Usuario autenticado
- **Precondición:** El usuario ha iniciado sesión y posee al menos una solicitud de amistad pendiente.
- **Escenario exitoso principal – Aceptar:**
    1. El usuario accede a la sección de solicitudes de amistad pendientes.
    2. El sistema muestra las solicitudes recibidas.
    3. El usuario selecciona una solicitud y presiona "Aceptar".
    4. El sistema cambia el estado de la solicitud a `ACEPTADA`.
    5. El sistema registra la relación de amistad entre ambos usuarios.
    6. El sistema actualiza la lista de amigos del usuario.
    7. El sistema informa que la solicitud fue aceptada correctamente.
- **Escenario alternativo – Rechazar:**
    - **3a. Rechazar solicitud:**
        1. El usuario selecciona una solicitud pendiente y presiona "Rechazar".
        2. El sistema cambia el estado de la solicitud a `RECHAZADA` o elimina la solicitud pendiente.
        3. El sistema confirma que la solicitud fue rechazada.
        4. Los usuarios no son agregados a sus respectivas listas de amigos.
- **Escenarios excepcionales:**
    - **3b. Solicitud ya procesada:** Si la solicitud ya fue aceptada o rechazada previamente, el sistema informa que ya no se encuentra pendiente y actualiza el listado.

# CU09 ELIMINADO 

## Módulo: Gestión de Plantel y Comportamientos
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


### CU11: Listar jugadores del club

* **Actor:** Usuario autenticado.
* **Precondición:** El usuario tiene una sesión activa.
* **Escenario exitoso principal:**
  1. El usuario navega al apartado de plantel.
  2. El sistema consulta la base de datos y recupera todos los jugadores activos (no eliminados) pertenecientes al club del usuario.
  3. El sistema muestra una vista con las tarjetas o tabla de cada jugador, mostrando:
     * Nombre del jugador.
     * Desglose de sus 5 atributos PACSS (Power, Agility, Control, Speed, Strength.
* **Escenarios excepcionales:**
  * **2a. El club no posee jugadores creados:** El sistema muestra una vista de los jugadores default brindados por el sistema y un botón de acceso directo a "Crear Jugador"

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

* **CU16:** Listar comportamientos del club
* **Actor:** Usuario autenticado.
* **Precondición:** El usuario ha iniciado sesión
* **escenario exitoso principal:**
  1. El usuario ingresa a la sección "Comportamientos"
  2. El sistema recupera de la base de datos todos los comportamientos vigentes asociados al club del usuario.
  3. El sistema muestra la lista de tácticas con su nombre, fecha de creación/modificación y las opciones de "Editar", "Ver" o "Eliminar".
* **escenarios excepcioanles:**
  * **2a. No existen comportamientos registrados:** El sistema muestra un mensaje indicando que el club aún no posee tácticas creadas junto a un botón para crear la primera

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


* **CU18:** Listar y buscar ligas disponibles

* **Actor:** Usuario autenticado
* **Precondición:** El usuario tiene una sesión activa
* **escenario exitoso principal:**
  1. El usuario abre "Explorar Ligas"
  2. El sistema consulta y presenta la lista de ligas públicas en estado `ABIERTA` y con cupos disponibles.
  3. Para cada liga, el sistema muestra: nombre, creador, cupos ocupados/totales (ej: 4/8) y duración de partidos
  4. El usuario puede filtrar por nombre.
  5. El sistema actualiza la lista según los filtros aplicados.
* **escenarios excepcionales:**
  * **2a. No hay ligas disponibles con cupo abierto:** El sistema muestra un mensaje indicando que no se encontraron ligas abiertas y ofrece la opción de "Crear Liga"

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

* **CU24:** Finalizar liga (automático tras la última ronda)

-   **Actor:** Sistema.
- **Precondición:** La liga se encu entra iniciada y todos los partidos correspondientes a todas sus rondas han finalizado.
- **Escenario exitoso principal:**
    1. El sistema verifica que todos los partidos del fixture hayan finalizado.
    2. El sistema actualiza la tabla de posiciones con los resultados de la última ronda.
    3. El sistema aplica los criterios de puntuación y desempate establecidos para determinar las posiciones finales.
    4. El sistema establece la clasificación definitiva de los clubes.
    5. El sistema cambia el estado de la liga a `FINALIZADA`.
    6. El sistema muestra el fixture completo, los resultados finales y la tabla de posiciones definitiva.
    7. El sistema informa a los clubes participantes que la liga ha finalizado.
- **Consideración para ligas públicas:**
    - Los resultados de los partidos disputados en una liga pública también se consideran para el Ranking Global.
- **Consideración para ligas privadas:**
    - Los resultados de la liga privada solamente afectan al ranking propio de la liga y no al Ranking Global.

---

## Módulo: Partidos y Simulación        (asumiendo que existe el sistema de amigos)
# CU25:ELIMINADO

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

 **CU28:** Observar partido en vivo   (a reveer)
*- **Actor:** Usuario autenticado perteneciente a la liga.
- **Precondición:** El club del usuario pertenece a la misma liga del partido que desea observar y el partido se encuentra en curso.
- **Escenario exitoso principal:**
    1. El usuario accede al fixture de la liga.
    2. El sistema identifica los partidos que se encuentran en curso.
    3. El usuario selecciona el partido que desea observar.
    4. El sistema muestra la representación en vivo del partido.
    5. Durante el encuentro, el sistema muestra la información actualizada del partido, incluyendo:
        - Clubes participantes.
        - Jugadores en cancha.
        - Marcador.
        - Tiempo restante.
        - Etapa actual del partido.
    6. Durante las pausas de hidratación y el entretiempo, el sistema informa que el partido se encuentra temporalmente pausado.
    7. Al finalizar el partido, el sistema muestra el resultado definitivo.
    8. El resultado queda reflejado en el fixture y en la tabla de posiciones correspondiente.
- **Escenarios excepcionales:**
    - **3a. Partido ya finalizado:** Si el partido finaliza antes de que el usuario acceda, el sistema muestra el resultado final en lugar de la vista en vivo.

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

### CU30: Realizar cambio en pausa (hidratación o entretiempo)

* **Actor:** Usuario autenticado (propietario de uno de los clubes en juego)
* **Precondición:** El partido está en curso y entra en una de las 3 pausas reglamentarias (hidratación 1, entretiempo, hidratación 2)
* **Escenario exitoso principal:**
1. El usuario toca "Realizar cambio".
2. 2. El sistema habilita en la vista el panel de control táctico. 
3. El usuario selecciona el jugador que desea cambiar. 
4. El sistema muestra los jugadores disponibles para dicho reemplazo. 
5. El usuario decide cuál quiere y presiona "confirmar cambios".
6. El sistema al finalizar la pausa refleja el cambio hecho. 
- **Escenario excepcional:**
	-  **6a. Intento de realizar más de una sustitución en la misma pausa:** El sistema bloquea el segundo cambio e informa que solo se permite una sustitución por pausa

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
* **CU32:** Consultar ranking global de clubes

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