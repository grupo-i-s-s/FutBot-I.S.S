# Diagrama de clases v0.1 - FutBot

Version conceptual inicial del modelo de dominio. El objetivo es representar las
entidades principales y reglas de negocio conocidas, sin cerrar detalles de
implementacion.

```mermaid
classDiagram
    direction LR

    class Usuario {
        +id
        +nombre
        +email
        +registrarse()
        +iniciarSesion()
    }

    class Club {
        +id
        +nombre
        +avatar
        +crearJugador(nombre, pacss)
        +eliminarJugador(jugador)
        +crearComportamiento(nombre, codigo)
        +editarComportamiento(comportamiento, codigo)
        +unirseALiga(liga, jugadores)
    }

    class Jugador {
        +id
        +nombre
        +activo
    }

    class PACSS {
        +power
        +agility
        +control
        +speed
        +strength
    }

    class Comportamiento {
        +id
        +nombre
        +codigo
        +estaEnUso()
    }

    class Liga {
        +id
        +nombre
        +privacidad
        +minClubes
        +maxClubes
        +duracionPartidos
        +estado
        +iniciar()
        +cancelar()
        +generarFixture()
    }

    class ParticipacionLiga {
        +fechaInscripcion
        +activa
        +validarPlantel()
    }

    class JugadorInscriptoLiga {
        +nombreSnapshot
        +pacssSnapshot
    }

    class Fixture {
        +generarTodosContraTodos()
    }

    class Partido {
        +id
        +fechaHora
        +duracion
        +estado
        +simular()
        +cambiarComportamiento()
    }

    class AlineacionPartido {
        +definirTitulares()
        +definirSuplentes()
        +cambiarFormacion()
    }

    class JugadorAlineado {
        +rol
    }

    class Formacion {
        +nombre
    }

    class SimulacionPartido {
        +ejecutar()
        +aplicarComportamientos()
        +actualizarResultado()
    }

    class Resultado {
        +golesLocal
        +golesVisitante
    }

    class TablaDePuntaje {
        +actualizarConResultado()
    }

    class EntradaTabla {
        +puntos
        +partidosJugados
        +ganados
        +empatados
        +perdidos
        +golesAFavor
        +golesEnContra
    }

    class PrivacidadLiga {
        <<enumeration>>
        PUBLICA
        PRIVADA
    }

    class EstadoLiga {
        <<enumeration>>
        ABIERTA
        INICIADA
        CANCELADA
        FINALIZADA
    }

    class EstadoPartido {
        <<enumeration>>
        PROGRAMADO
        EN_CURSO
        FINALIZADO
    }

    class RolAlineacion {
        <<enumeration>>
        TITULAR
        SUPLENTE
    }

    Usuario "1" *-- "1" Club : posee

    Club "1" *-- "0..*" Jugador : plantilla actual
    Jugador "1" *-- "1" PACSS : estadisticas

    Club "1" *-- "0..*" Comportamiento : define

    Club "1" --> "0..*" Liga : crea
    Club "1" --> "0..*" ParticipacionLiga : participa

    Liga "1" *-- "3..*" ParticipacionLiga : inscripciones
    ParticipacionLiga "1" --> "1" Club : club
    ParticipacionLiga "1" --> "1" Liga : liga
    ParticipacionLiga "1" *-- "6" JugadorInscriptoLiga : plantel fijo

    JugadorInscriptoLiga "0..1" --> "1" Jugador : origen
    JugadorInscriptoLiga "1" *-- "1" PACSS : copia estadisticas

    Liga "1" *-- "1" Fixture : fixture
    Fixture "1" *-- "1..*" Partido : partidos

    Liga "1" *-- "1" TablaDePuntaje : tabla
    TablaDePuntaje "1" *-- "3..*" EntradaTabla : posiciones
    EntradaTabla "1" --> "1" ParticipacionLiga : club en liga

    Partido "1" --> "1" ParticipacionLiga : local
    Partido "1" --> "1" ParticipacionLiga : visitante
    Partido "1" *-- "2" AlineacionPartido : alineaciones
    Partido "1" *-- "0..1" Resultado : resultado
    Partido "1" *-- "1" SimulacionPartido : simulacion

    AlineacionPartido "1" --> "1" ParticipacionLiga : de club
    AlineacionPartido "1" *-- "6" JugadorAlineado : jugadores
    AlineacionPartido "1" --> "1" Formacion : formacion

    JugadorAlineado "1" --> "1" JugadorInscriptoLiga : jugador
    JugadorAlineado "1" --> "1" Comportamiento : comportamiento activo

    Liga --> PrivacidadLiga
    Liga --> EstadoLiga
    Partido --> EstadoPartido
    JugadorAlineado --> RolAlineacion
```

## Reglas de negocio representadas

- Cada usuario posee un unico club.
- El avatar pertenece al club.
- Un club puede tener jugadores ilimitados.
- Los jugadores se crean con nombre y estadisticas PACSS. Luego no se editan.
- PACSS esta compuesto por power, agility, control, speed y strength.
- Los comportamientos pertenecen al club y tienen nombre y codigo.
- Un club puede crear comportamientos repetidos si quiere.
- Durante un partido se pueden cambiar comportamientos activos, pero no crear ni
  editar comportamientos.
- Como un club puede jugar partidos simultaneamente, el comportamiento activo se
  modela dentro de `JugadorAlineado`, es decir, en el contexto de un partido.
- Un club puede participar en varias ligas.
- Una liga es todos contra todos.
- Una liga tiene minimo 3 clubes. El maximo lo define el club creador.
- Para unirse a una liga, el club debe seleccionar exactamente 6 jugadores.
- Esos 6 jugadores quedan guardados en la participacion de esa liga hasta que la
  liga termine.
- Si un jugador se elimina del club durante la liga, sigue existiendo como
  `JugadorInscriptoLiga` dentro de esa liga.
- Antes de cada partido se define una alineacion con 3 titulares, 3 suplentes y
  una formacion.
- Los titulares, suplentes y la formacion pueden cambiar antes de cada partido,
  pero siempre usando los 6 jugadores inscriptos en la liga.
- El partido puede simularse sin que el usuario intervenga, ya que los
  comportamientos actuan automaticamente.

## Decisiones abiertas para proximas versiones

- Detallar la clase `Formacion` con posiciones concretas.
- Definir si habra eventos de partido, por ejemplo goles, pases, choques,
  cambios de comportamiento o sustituciones.
- Definir como se valida que un comportamiento esta en uso.
- Definir reglas exactas de puntaje de la tabla.
- Definir si los partidos tienen fecha programada fija o se ejecutan apenas
  ambos clubes tienen alineacion.
