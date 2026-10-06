import pygame
import pymunk.pygame_util
from argparse import ArgumentParser
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

from app.database import engine
from app.services.match_builder_service import build_match


def probar_simulacion(match_id: int) -> None:
    print("Conectando a la base de datos...")
    with Session(engine) as db:
        mi_partido = build_match(db, match_id)

    print(
        "Jugadores en cancha:",
        [(player.id, player.name) for player in mi_partido.player_profiles],
    )

    # 3. CONFIGURAMOS PYGAME
    pygame.init()
    pantalla = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Test Visual de Fútbol con SQLAlchemy")
    reloj = pygame.time.Clock()

    opciones_dibujo = pymunk.pygame_util.DrawOptions(pantalla)
    opciones_dibujo.transform = pymunk.Transform.scaling(10.0)

    fps = 60
    dt = 1.0 / fps
    corriendo = True

    print("Iniciando el partido... Cerrá la ventana para salir.")

    while corriendo:
        # A. Eventos
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False

        # B. Lógica (El Cerebro)
        mi_partido.run_match(dt)
        if mi_partido.finished:
            print("Partido finalizado:", mi_partido.scorer)
            corriendo = False

        # C. Renderizado Visual
        pantalla.fill((34, 139, 34))
        mi_partido.world.space.debug_draw(opciones_dibujo)
        pygame.display.flip()

        # D. Control de velocidad
        reloj.tick(fps)

    pygame.quit()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("match_id", type=int)
    args = parser.parse_args()
    probar_simulacion(args.match_id)
