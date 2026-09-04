# Alcance de FutBot

**I.S.S (Ingeniería del Software Survival)**
Fecha: 21/08/2026
Versión del documento: 0.7


FutBot es un videojuego en línea en el cual se pueden jugar partidos de fútbol en vivo entre clubes.

Para poder comenzar a jugar, el usuario deberá registrarse, cada mail podrá tener un único usuario. Además deberá configurar su club decidiendo el nombre y eligiendo su avatar.



El sistema te proporciona 6 jugadores default con 1 comportamiento para jugar, una vez dentro del club el usuario podrá comenzar a crear sus propios jugadores y comportamientos. Podrá crear o participar en partidos amistosos, contra clubes que estén disponibles.  Además al usuario se le habilitan la participación en las ligas, donde podrá crear / unirse, iniciar (sólo si es el creador), cancelar (si es club creador) /  (si no es club creador) abandonar, sólo si la liga no ha iniciado. Existen ligas privadas y públicas, dentro de cada liga hay un ranking propio de la misma.


  --- 
## El sistema esta conformado por las siguentes partes:

## Usuarios

Para registrar un usuario, se deberá completar un formulario con los siguientes campos:

- Nombre
- **Username** (único)
- email (debe ser único)
- password (deberá repetirla para validar)

Una vez creado el usuario, necesitará los datos de email y password para iniciar sesión.

---
### Clubes

Al registrarse, el usuario también deberá configurar su club con un nombre y avatar.
El avatar lo decide desde una biblioteca de avatares brindada por el sistema. Puede editarlo cuantas veces desee el usuario.

Para comenzar a jugar partidos ya sea en ligas o amistosos deberá definir un **equipo default** conformado por:

- 3 jugadores titulares.
- 3 jugadores suplentes.
- Cada jugador con su comportamiento, pudiendo repetir el mismo comportamiento en distintos jugadores.
- Formación. (Desde una biblioteca de formaciones, preestablecida por el sistema).


---

## Jugadores

El usuario podrá crear tantos jugadores como desee. Para ello deberá asignarle un nombre y completar PACSS*. Cada una de estas habilidades debe tener entre 20 y 100 puntos y la suma total de las 5 debe dar exactamente 300.

- **Power:** Fuerza con la que patea.
- **Agility:** Cada cuánto puede volver a patear.
- **Control:** Desde qué distancia alcanza a tocar la pelota.
- **Speed:** Qué tan rápido corre y acelera.
- **Strength:** Cuánto se impone en los choques.

Se pueden eliminar jugadores siempre y cuando no haya ningún partido en curso (la eliminación será lógica).
  

---

## Comportamientos

Se pueden crear tantos como el usuario desee. Deberá asignarle un nombre al comportamiento y el código correspondiente, el usuario codificará los comportamientos a través de programación en bloque.  Estos se pueden editar y/o eliminar, siempre y cuando no haya partidos en curso (la eliminación es lógica). 
La programación en bloque se hará a partir de ciertas primitivas brindadas por el sistema.

- **Correr()**
- **Patear()**
  

---

## Partido

Los partidos tendrán una duración de 5 con un entretiempo, y dos pausas de hidratación que dividen el tiempo entre inicio/fin y entretiempo en exactamente 4 tiempos iguales.  

<small> Es decir: inicio - <i>juego</i> - pausa hidratación 1 - <i>juego</i> - entretiempo - <i>juego</i> - pausa hidratación 2 - <i>juego</i> - fin </small>

Durante el partido se pueden cambiar los comportamientos de los jugadores por otros ya existentes.
Además se puede planear un cambio de jugador durante el tiempo de juego el cual se ve reflejado luego de alguna pausa o entretiempo, estos NO SON ACUMULABLES, es decir, por cada momento de juego, existe un único cambio, si no se planeó/realizó el cambio luego alguna pausa, no se habilitan 2 cambios para el siguiente momento de juego, seguirá siendo uno solo.

### Amistoso

Es un partido entre dos clubes fuera de liga, cuyo resultado no suma puntos al ranking global. 
Para poder participar en algún amistoso, el club deberá mostrarse como "disponible" para amistosos. 
El club podrá crear partido y decidir horario de inicio, se unirá con el equipo default del mismo pero podra realizar cambios en el equipo si lo desea antes de comenzar. 
Al "matchear" con otro club el partido se iniciara en el horario estipulado, si no hay match, se cancela. 
  

---

## Ranking

El sistema contará con un ranking global que incluye a TODOS los clubes existentes en el sistema.

Cada partido ganado sumará 3 puntos, el empate 1 y la derrota 0.

En caso de empate, se decidirá en el siguiente orden: diferencia de goles, goles a favor, por último, goles en contra.
  

---

## Ligas

Al participar en una liga el usuario se inscribirá con el equipo default definido en su club. Antes de cada partido podrá modificar las titularidades, suplencias y los comportamientos de sus jugadores. Si el usuario está offline al comenzar el partido, se jugará con el equipo default.

Cada liga tiene su propio ranking.

Cualquier usuario que pertenezca a una liga, podrá ver los partidos que se están jugando en la misma.

Para **crear** una liga se debe designar un mínimo de clubes (al menos 3), un máximo y una accesibilidad, ya sea privada o pública y el tiempo de juego en los partidos (en el momento, diariamente o semanalmente). Una vez que se cumpla el mínimo, solo el creador podrá iniciarla.

**Antes de que se inicie una liga**:
- El club creador puede cancelar la liga. Todos los clubes serán eliminados de la misma.
- Cualquier club unido a la liga podrá abandonarla.

### Fixture y rondas
La liga se juega formato todos contra todos.

- Existe un fixture que incluye horario de partidos, rondas a jugar y enfrentamientos.
- Cada par de clubes se enfrentará una única vez.
- Todos los partidos de una misma ronda se juegan simultáneamente.
- Hay un tiempo de espera que elige el creador de liga que puede ser de 2 minutos, 24 horas o 7 dias entre ronda y ronda.
- La liga finalizará al cumplirse todas las rondas.
- Si el equipo no está presente, el partido se juega igual con el equipo default.


### Privadas

Se ingresa con un codigo que proporciona el sistema al creador de la liga.
Los puntos NO sumarán en el ranking global.

### Públicas

Los puntos acumulados suman al ranking global.
Los clubes se pueden unir a cualquier liga disponible no iniciada.
  

---

## El proyecto NO abarcara con lo siguente (REVISAR)

  

El sistema NO contará con

- Editar jugadores ya creados.

- Sistemas de transferencia/prestamos de jugadores entre clubes.

- Compra/venta de jugadores entre clubes.

- Compra/venta de jugadores con el sistema.

- Sistema de microtransacciones dentro del juego.

- Sistema de repetición de los partidos.

- Sistema para crear formaciones.

- Otros formatos de ligas/competiciones.

- Chat de texto/voz entre clubes, ni sistema de mensajeria.

- Carga de fotos desde su ordenador ni via web. 

- Juego de partidos en simultáneo, ya sean ligas u amistosos. 
