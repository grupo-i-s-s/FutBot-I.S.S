import random
import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.league_model import League

# Devuelve una ronda y que club descansa o no
@dataclass
class RoundDraw:
    number: int
    pairings: list[tuple[int, int]]
    bye_club_id: int | None = None


def generate_league_rounds(db: Session, league: League) -> list[RoundDraw]:
    club_ids = [registration.club_id for registration in league.registrations]
    seed = league.draw_seed
    if seed is None:
        seed = secrets.randbits(63)

    rounds = generate_rounds(club_ids, seed=seed)
    league.draw_seed = seed
    db.flush()
    return rounds


# Genera todas las rondas del fixture
def generate_rounds(club_ids: list[int], *, seed: int) -> list[RoundDraw]:
    _validate_inputs(club_ids, seed)

    participants: list[int | None] = sorted(club_ids)

    rng = random.Random(seed)
    rng.shuffle(participants)

    if len(participants) % 2 != 0:
        participants.append(None)

    rounds: list[RoundDraw] = []
    total_rounds = len(participants) - 1
    pairings_per_round = len(participants) // 2

    for round_number in range(1, total_rounds + 1):
        pairings: list[tuple[int, int]] = []
        bye_club_id: int | None = None

        for index in range(pairings_per_round):
            first = participants[index]
            second = participants[-1 - index]

            if first is None:
                bye_club_id = second
            elif second is None:
                bye_club_id = first
            else:
                pairings.append((first, second))

        rounds.append(
            RoundDraw(
                number=round_number,
                pairings=pairings,
                bye_club_id=bye_club_id,
            )
        )

        # Metodo del circulo: mantener el primero y rotar los restantes.
        participants = [
            participants[0],
            participants[-1],
            *participants[1:-1],
        ]

    return rounds


# valida las entradas de los id de los clubes
def _validate_inputs(club_ids: list[int], seed: int) -> None:
    if not isinstance(club_ids, list):
        raise ValueError("Los clubes deben recibirse como una lista.")

    if len(club_ids) < 3:
        raise ValueError("Se necesitan al menos tres clubes.")

    if any(type(club_id) is not int or club_id <= 0 for club_id in club_ids):
        raise ValueError("Los IDs de clubes deben ser enteros positivos.")

    if len(club_ids) != len(set(club_ids)):
        raise ValueError("Los IDs de clubes no pueden repetirse.")

    if type(seed) is not int:
        raise ValueError("La semilla debe ser un número entero.")
