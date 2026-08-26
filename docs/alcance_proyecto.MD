# Alcance de FutBot

**I.S.S. (Ingeniería del Software Survival)**  
Fecha: 26/08/2026  
Versión del documento: 0.3  
Estado: borrador

## Resumen

FutBot es un videojuego en línea en el que los usuarios crean y administran su
propio club de fútbol. Cada club puede crear jugadores, definir comportamientos
para esos jugadores y participar en partidos amistosos o ligas públicas y
privadas.

Los partidos se simulan automáticamente a partir de las estadísticas de los
jugadores, la formación elegida y los comportamientos asignados. El usuario puede
intervenir durante un partido cambiando comportamientos o planificando cambios
de jugadores, pero el partido no depende de que el usuario esté presente para
jugarse.

## Objetivos

- Permitir que cada usuario registre una cuenta e inicie sesión.
- Permitir que cada usuario administre un único club.
- Permitir que cada club cree jugadores con estadísticas propias.
- Permitir que cada club cree comportamientos programados para sus jugadores.
- Permitir que los usuarios gestionen amistades.
- Permitir que los clubes jueguen partidos amistosos.
- Permitir que los clubes creen ligas o se unan a ligas existentes.
- Simular partidos entre clubes usando jugadores, formaciones y comportamientos.
- Mantener fixtures, resultados, rankings de liga y ranking global.

## Actores principales

- **Usuario:** persona que se registra en el sistema y administra un club.
- **Club:** entidad administrada por un usuario. Participa en ligas, posee
  jugadores y define comportamientos.
- **Sistema de simulación:** componente encargado de ejecutar los partidos de
  forma automática.

## Usuarios y clubes

Para registrarse, el usuario debe completar un formulario con:

- nombre;
- username;
- email único;
- password, con repetición para validación.

Una vez registrado, el usuario inicia sesión con email y password. Luego puede
configurar su club, definiendo nombre y avatar.

Reglas principales:

- Cada usuario posee un único club.
- El avatar pertenece al club.
- El avatar se elige desde una biblioteca provista por el sistema.
- El usuario puede cambiar el avatar del club cuantas veces desee.
- Un club puede participar en varias ligas al mismo tiempo.
- Un club puede jugar varios partidos simultáneamente.

## Jugadores

El club puede crear tantos jugadores como desee. Cada jugador se crea con nombre
y estadísticas PACSS.

PACSS está compuesto por:

- **Power:** fuerza con la que patea.
- **Agility:** cada cuánto puede volver a patear.
- **Control:** desde qué distancia alcanza a tocar la pelota.
- **Speed:** qué tan rápido corre y acelera.
- **Strength:** cuánto se impone en los choques.

Reglas principales:

- Cada valor de PACSS debe estar entre 20 y 100 puntos.
- La suma total de los cinco valores debe ser exactamente 300.
- Los jugadores no se pueden editar luego de ser creados.
- La eliminación de jugadores es lógica.
- No se pueden eliminar jugadores mientras el club tenga un partido en curso.
- Si un jugador eliminado estaba inscripto en una liga en curso, sus datos se
  conservan dentro de esa liga hasta que finalice.
- Si un jugador participa en más de un partido simultáneamente, sus acciones son
  independientes en cada partido.

## Comportamientos

Los comportamientos definen la lógica con la que actúan los jugadores durante
los partidos.

Reglas principales:

- Los comportamientos pertenecen al club.
- Cada comportamiento tiene nombre y código.
- El código se genera mediante programación en bloques.
- El club puede crear tantos comportamientos como quiera.
- Se permiten comportamientos que hagan lo mismo.
- No existe una acción específica para copiar o duplicar comportamientos.
- Mientras el club tenga un partido en curso, no se pueden crear, editar ni
  eliminar comportamientos.
- La eliminación de comportamientos es lógica.
- Durante un partido se puede cambiar el comportamiento activo en cualquier momento de un jugador por
  otro comportamiento disponible para ese partido.
- Cambiar un comportamiento en un partido no modifica el comportamiento usado por
  el mismo jugador en otro partido simultáneo.
- Al unirse a una liga, los comportamientos disponibles para esa liga quedan
  guardados como estaban en ese momento.
- Si luego se crean, editan o eliminan comportamientos del club, esos cambios
  aplican para futuras ligas o amistosos, pero no modifican la liga ya iniciada
  o la inscripción ya realizada.

## Amigos

El sistema permite que los usuarios se vinculen entre sí para jugar partidos
amistosos.

- El usuario puede buscar a otro usuario por username.
- El usuario puede enviar solicitudes de amistad.
- El usuario puede recibir solicitudes de amistad.
- El usuario puede aceptar o rechazar solicitudes de amistad.
- Para invitar a un amistoso, el rival debe ser un amigo.

## Partidos amistosos

Los partidos amistosos permiten jugar fuera de una liga.

Reglas principales:

- Para jugar un amistoso, el club debe tener al menos 6 jugadores y al menos 1
  comportamiento.
- Para jugar un amistoso, el club debe seleccionar 6 jugadores, definir 3
  titulares, 3 suplentes, una formación y comportamientos iniciales.
- El usuario puede invitar a un amigo a jugar un partido amistoso.
- Los amistosos pueden simularse aunque los usuarios no estén presentes.
- El resultado de un amistoso no suma puntos al ranking global.

## Ligas

Las ligas son competencias entre clubes con formato todos contra todos.

Para crear una liga, el club creador define:

- nombre;
- accesibilidad: pública o privada;
- cantidad mínima de clubes;
- cantidad máxima de clubes;
- duración de los partidos.

Reglas principales:

- La cantidad mínima de clubes por defecto es 3.
- El creador puede elegir un mínimo mayor, pero nunca menor a 3.
- La cantidad máxima de clubes la define el creador.
- Si una liga llega al máximo de clubes, no se pueden enviar nuevas solicitudes
  ni unirse a esa liga.
- Cuando una liga llega al máximo de clubes, queda esperando a que el anfitrión
  la inicie.
- El club creador puede iniciar la liga cuando se cumple la cantidad mínima de
  clubes.
- Si el creador abandona la liga antes de iniciarla, la liga se cancela.
- El club creador puede cancelar la liga si todavía no fue iniciada.
- Cualquier club participante puede abandonar la liga mientras todavía no haya
  iniciado.
- Cada liga tiene su propio ranking o tabla de posiciones.
- Los partidos de ligas públicas suman puntos al ranking global.
- Los partidos de ligas privadas no suman puntos al ranking global.

### Ligas privadas

- Se puede ingresar por invitación.
- Se puede ingresar por código.
- Sus partidos no suman puntos al ranking global.

### Ligas públicas

- Los clubes pueden unirse a cualquier liga pública disponible, siempre que haya
  cupo.
- Sus partidos suman puntos al ranking global.

## Inscripción a una liga

Para solicitar unirse a una liga, el club debe dejar definida la información
necesaria para poder jugar aunque el usuario no esté presente.

Requisitos:

- El club debe tener al menos 6 jugadores.
- El club debe tener al menos 1 comportamiento.
- El club debe seleccionar exactamente 6 jugadores para esa liga.
- El club debe definir 3 titulares y 3 suplentes iniciales.
- El club debe definir una formación inicial.
- Cada jugador seleccionado debe tener un comportamiento inicial asignado.

Reglas principales:

- Los 6 jugadores seleccionados quedan fijos para esa liga.
- Los jugadores seleccionados no pueden reemplazarse durante la liga.
- Los titulares, suplentes y la formación inicial funcionan como configuración
  por defecto.
- Antes de cada partido se pueden cambiar titulares, suplentes y formación, pero
  siempre usando los mismos 6 jugadores inscriptos.
- Si el usuario no modifica la alineación antes de un partido, se usa la
  configuración por defecto.
- Si uno de los jugadores inscriptos se elimina de la plantilla actual del club,
  sigue guardado dentro de esa liga hasta que la liga finalice.
- Las estadísticas y comportamientos guardados para la liga no cambian aunque el
  club edite información fuera de esa liga.

## Fixture y rondas

La liga se juega con formato todos contra todos a partido único.

Reglas principales:

- Cada par de clubes se enfrenta una sola vez.
- No hay ida y vuelta.
- El fixture organiza los partidos en rondas.
- Todos los partidos de una misma ronda se juegan simultáneamente.
- Cuando finalizan todos los partidos de una ronda, el sistema espera **(preguntar)** 1,5 minutos antes de iniciar la siguiente ronda.
- **El tiempo de espera entre rondas queda como valor configurable o a definir.**
- El proceso se repite hasta que se juegan todas las rondas y finaliza la liga.

## Partidos

Cada partido enfrenta a dos clubes y puede ejecutarse automáticamente por el
sistema de simulación.

Reglas principales:

- En ligas, la duración del partido la define el creador de la liga.
- Cada partido se juega con 3 titulares por club.
- Cada club dispone de 3 suplentes.
- El partido puede simularse aunque los usuarios no estén presentes.
- Durante el partido los jugadores actúan según sus comportamientos activos.
- Durante el partido el usuario puede cambiar comportamientos activos, pero no
  crear ni editar comportamientos.
- Los cambios de comportamiento afectan únicamente al partido en el que se
  realizan.
- Un mismo jugador puede participar en partidos simultáneos con comportamientos
  distintos en cada uno.
- Al finalizar el partido se registra el resultado.

### Pausas y cambios de jugadores

Cada partido tiene tres pausas:

- pausa de hidratación a la mitad del primer tiempo;
- entretiempo;
- pausa de hidratación a la mitad del segundo tiempo.

Reglas de cambios:

- Cada club puede realizar como máximo 3 cambios de jugadores por partido.
- Solo se puede realizar 1 cambio por pausa.
- El cambio puede solicitarse antes de la pausa para que se aplique al llegar a
  esa pausa.
- El cambio también puede realizarse directamente durante la pausa.
- Si en una pausa no se realiza un cambio, ese cambio se pierde.
- Los cambios no son acumulables.
- Puede volver a entrar un jugador que ya había salido, siempre respetando el
  límite de 1 cambio por pausa y 3 cambios totales.

## Rankings

Cada liga tiene una tabla de posiciones propia. Además, existe un ranking global
alimentado por partidos de ligas públicas.

Reglas principales:

- Victoria: 3 puntos.
- Empate: 1 punto.
- Derrota: 0 puntos.
- El ranking global usa la misma lógica de puntos.
- Los amistosos no suman al ranking global.
- Las ligas privadas no suman al ranking global.

Criterios de desempate:

- puntos;
- diferencia de goles;
- goles a favor.

Si el empate persiste después de esos criterios, el criterio siguiente queda a
definir.


## Puntos pendientes o decisiones abiertas

- Definir el valor final del tiempo de espera entre rondas, actualmente pensado
  como 1,5 minutos.
- Definir si los partidos amistosos tienen una duración configurable y quién la
  elige.
- Definir si las solicitudes para ligas públicas requieren aceptación del creador
  o si el ingreso es automático mientras haya cupo.
- Definir los criterios de desempate posteriores a puntos, diferencia de goles y
  goles a favor.
- Definir con más detalle las formaciones y posiciones.
- Definir los eventos relevantes de la simulación: goles, pases, choques,
  remates, cambios de comportamiento, faltas, etc.
- Definir el lenguaje o estructura exacta del código generado por la
  programación en bloques.
- Duracion de las pausas.
