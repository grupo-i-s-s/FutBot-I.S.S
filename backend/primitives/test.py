import pygame
import pymunk.pygame_util
from sqlalchemy import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv  # Importamos la librería

# 1. CARGAMOS LAS VARIABLES DE ENTORNO
load_dotenv()  # Esto lee tu archivo .env y lo mete en la memoria

# 2. AHORA SÍ IMPORTAMOS LA BASE DE DATOS
# Como load_dotenv ya hizo su trabajo, database.py va a encontrar a POSTGRES_USER
from app.database import engine
from app.models.player_model import Player

from primitives.match_simulation import Partido, Team


def get_jugadores_por_club(db: Session, id_club: int):
    """Busca en la BD todos los jugadores activos de un club específico."""
    stmt = select(Player).where(Player.club_id == id_club, Player.is_deleted == False)
    return list(db.scalars(stmt).all())


def probar_simulacion():
    # 1. CONSULTA A LA BASE DE DATOS
    print("Conectando a la base de datos...")
    with Session(engine) as db:
        # Reemplazá el 1 y el 2 por IDs de clubes que sepas que existen en tu tabla clubs
        jugadores_local = get_jugadores_por_club(db, 1)
        jugadores_visita = get_jugadores_por_club(db, 2)

        # Armamos tus clases Team con las listas de objetos Player reales
        team_local = Team(name="Equipo Local (ID 1)", players=jugadores_local)
        team_visita = Team(name="Equipo Visitante (ID 2)", players=jugadores_visita)

        print(
            f"Equipos cargados: {len(team_local.players)} jug. vs {len(team_visita.players)} jug."
        )

    # 2. INSTANCIAMOS EL PARTIDO CON LOS DATOS REALES
    # Recordá que el __init__ de tu clase Partido ahora debe recibir (team_local, team_visita)
    mi_partido = Partido(team_local, team_visita)

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

        # C. Renderizado Visual
        pantalla.fill((34, 139, 34))
        mi_partido.world.space.debug_draw(opciones_dibujo)
        pygame.display.flip()

        # D. Control de velocidad
        reloj.tick(fps)

    pygame.quit()


if __name__ == "__main__":
    probar_simulacion()
