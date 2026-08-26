# Alcance de FutBot

**I.S.S (Ingeniería del Software Survival)**
Fecha: 21/08/2026
Versión del documento: 0.2

FutBot es un videojuego en línea en el cual se pueden jugar partidos de fútbol en vivo entre clubes.

El usuario deberá registrarse con nombre, **username** (único), password y un email único, es decir, cada mail podrá tener un único usuario. Una vez registrado podrá crear su club, decidiendo el nombre y eligiendo su avatar.
Una vez dentro del club el usuario podrá comenzar a crear sus propios jugadores y comportamientos. 
Al tener 3 o más jugadores y al menos 1 comportamiento, podrá crear partidos amistosos seleccionando rival entre sus amigos en línea.  Para hacer amigos deberá buscar a quien desee por username y enviar la solicitud de amistad.
Al tener 6 o más jugadores y al menos 1 comportamiento al usuario se le habilitan la participación en las ligas, donde podrá crear / unirse, iniciar (sólo si es el creador), cancelar (si es club creador) /  (si no es club creador) abandonar, sólo si la liga no ha iniciado. Existen ligas privadas y públicas, dentro de cada liga hay un ranking propio de la misma y cada partido de liga pública también suma puntos a un ranking global. Para formar parte de una liga el club deberá decidir 3 jugadores titulares y 3 suplentes los cuales utilizará en todos los partidos de la misma. 

---
## Usuarios 
Para registrar un usuario, se deberá completar un formulario con los siguientes campos: 
- Nombre
- **Username** (único)
- email (debe ser único)
- password (deberá repetirla para validar)
Una vez creado el usuario, necesitará los datos de email y password para iniciar sesión. Luego podrá configurar su club con un nombre y avatar. 
El avatar lo decide desde una biblioteca de avatares brindada por el sistema. Puede editarlo cuantas veces desee el usuario. 

---
## Jugadores 
El usuario podrá crear tantos jugadores como desee. Para ello deberá asignarle un nombre y completar PACSS(Power, Agility, Control, Strength, Speed). Cada una de estas habilidades debe tener entre 20 y 100 puntos y la suma total de las 5 debe dar exactamente 300. 
Se pueden eliminar jugadores siempre y cuando no haya ningún partido en curso (la eliminación será lógica).

---
## Comportamientos
Se pueden crear tantos como el usuario desee. Deberá asignarle un nombre al comportamiento y el código correspondiente, el usuario codificará los comportamientos a través de programación en bloque.  Estos se pueden editar y/o eliminar, siempre y cuando no haya partidos en curso (la eliminación es lógica).

---
## Amigos
El usuario podrá enviar solicitudes de amistad a cualquier otro usuario. Para ello deberá buscar a quien desee enviar solicitud por username. 
También puede recibir solicitudes y decidir si aceptarlas o no. 

---
## Partido 
Los partidos tendrán una duración de ***COMPLETAR*** con un entretiempo, y dos pausas de hidratación que dividen el tiempo entre inicio/fin y entretiempo.  
<small> Es decir: inicio - <i>juego</i> - pausa hidratación 1 - <i>juego</i> - entretiempo - <i>juego</i> - pausa hidratación 2 - <i>juego</i> - fin </small>

Durante el partido se pueden cambiar los comportamientos de los jugadores por otros ya existentes.
Además se puede planear un cambio de jugador durante el tiempo de juego el cual se ve reflejado luego de alguna pausa o entretiempo, estos NO SON ACUMULABLES, es decir, por cada momento de juego, existe un único cambio, si no se planeó/realizó el cambio luego alguna pausa, no se habilitan 2 cambios para el siguiente momento de juego, seguirá siendo uno solo. 
### Amistoso
Podrá enviar una invitación a sus amigos en línea para jugar un partido amistoso. El resultado de este no se verá reflejado en el ranking global. 

---
## Ligas 
Para poder participar en una liga, el club deberá tener al menos 6 jugadores y decidir por 3 titulares y 3 suplentes. Si bien esto puede cambiar antes de cada partido, se exige decidir así para si el usuario está offline al comenzar el partido, se toma como equipo default. 
Cada liga tiene su propio ranking.

Para **crear** una liga se debe designar un mínimo de jugadores (al menos 3) y un máximo y una accesibilidad, ya sea privada o pública. Una vez que se cumpla el mínimo, solo el creador podrá iniciarla. 

**Antes de que se inicie una liga**: 
- El club creador puede cancelar la liga. Todos los clubes serán eliminados de la misma. 
- Cualquier club unido a la liga podrá abandonarla. 
### Privadas 
Se ingresa con una invitación.
Los puntos no sumarán en el ranking global. 
### Públicas 
Los puntos acumulados suman al ranking global. 
Los clubes se pueden unir a cualquier liga disponible. 

--- 
