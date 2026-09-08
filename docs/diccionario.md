# DICCIONARIO DEL DIAGRAMA DE FLUJO DE DATOS

## DFD General
Equipo_default = jugador1 + jugador2 + jugador3 + jugador4 + jugador5 + jugador6 + comportamiento 
Datos_de_registro = Nombre_Club + email + Username + contaseña + nombre
Nuevo_club = Datos_de_registro + avatar + Equipo_default
Datos_jugador = name + PACSS 
Nuevo_jugador = Datos_jugador + id_club
Plantilla = jugador1 + jugador2 + jugador3 + jugador4 + jugador5 + jugador6 + [comportamiento]* + formacion
Estadísticas_partido = goles_club1 + goles_club2 + id_club1 + id_club2
Max_min = min_cant_clubes + max_cant_clubes
Codigo = [primitiva] *
Nuevo_comportamiento = código + nombre + id_comportamiento

## DFD Partido 

partido_programado = datos_de_partido + estadisticas
datos_de_partido = horario + fecha_inicio + usuario_creador
lista_comportamientos = nombre_comportamientos + código correspondiente
jugador# =  PACSS + nombre
cambio_planeado = jugador + jugador_entrante
lista_jugadores_club = PACSS + nombres
jugador_entrante = PACSS + nombre
cambios = jugador1 + jugador2 + jugador3 + jugador4 + jugador5 + jugador6 + [comportamiento]* + formacion (actualizados)
nueva_formación = jugador1 + jugador2 + jugador3 + jugador4 + jugador5 + jugador6
nuevo_comportamiento = jugador# + nomrbre_comportamiento


## DFD Ligas


## DFD Club
comportamiento = nombre + código
datos_comportamiento = nombre + código
PACSS = power + agility + control + speed + strength 
jugador_comportamiento = id_comportamiento + id_jugador 
eliminación_comportamiento = id_comportamiento + false 
eliminación_jugador = id_jugador + false 
datos_club = avatar + nombre 
cambio_jugadores = id_jugador1 + id_jugador2

## DFD Registro