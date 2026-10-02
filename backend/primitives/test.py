import pygame
import pymunk.pygame_util

# Importamos tu clase orquestadora
from match_simulation import Partido

# 1. Instanciamos tu partido (ya crea la cancha, jugadores y pelota)
mi_partido = Partido()

# 2. Configuramos Pygame
pygame.init()
# Como tu cancha tiene 100 de ancho y 60 de alto, la multiplicamos por 10 para la ventana
pantalla = pygame.display.set_mode((1000, 600))
pygame.display.set_caption("Test Visual de la Clase Partido")
reloj = pygame.time.Clock()

# Configuramos Pymunk para que dibuje y le aplicamos un zoom x10
opciones_dibujo = pymunk.pygame_util.DrawOptions(pantalla)
opciones_dibujo.transform = pymunk.Transform.scaling(10.0)

fps = 60
dt = 1.0 / fps
corriendo = 0.0

print("Iniciando el partido... Cerrá la ventana para salir.")

while corriendo < 800:
    # A. Chequear si cerraste la ventana
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            corriendo = False

    # B. EL CEREBRO: Llamamos a tu método maestro.
    # Esto mueve a los 6 jugadores, avanza la física y chequea los goles.
    mi_partido.run_match(dt)

    # Opcional: Imprimir el marcador si alguien metió gol
    # (Podrías agregar un print acá para ver los goles en consola)

    # C. RENDERIZADO VISUAL
    pantalla.fill((34, 139, 34))  # Fondo verde
    # Le pedimos a Pymunk que dibuje el espacio que está adentro de tu mundo
    mi_partido.world.space.debug_draw(opciones_dibujo)
    pygame.display.flip()

    # D. Control de velocidad
    reloj.tick(fps)

pygame.quit()
