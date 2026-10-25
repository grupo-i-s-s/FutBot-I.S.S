from dataclasses import dataclass


@dataclass(frozen=True)
class Formation:
    id: int
    name: str
    description: str
    positions: tuple[tuple[float, float], ...]
    labels: tuple[str, ...]


# Coordenadas normalizadas sobre la cancha completa.
# Se definen desde el lado izquierdo, atacando hacia la derecha.
# El visitante refleja la coordenada X.
FORMATIONS = {
    1: Formation(
        id=1,
        name="2-1",
        description="Dos jugadores retrasados y uno adelantado.",
        positions=((0.18, 0.30), (0.18, 0.70), (0.30, 0.50)),
        labels=("Atrás arriba", "Atrás abajo", "Adelante"),
    ),
    2: Formation(
        id=2,
        name="1-2",
        description="Un jugador retrasado y dos adelantados.",
        positions=((0.18, 0.50), (0.30, 0.30), (0.30, 0.70)),
        labels=("Atrás", "Adelante arriba", "Adelante abajo"),
    ),
    3: Formation(
        id=3,
        name="1-1-1",
        description="Tres jugadores escalonados por el centro.",
        positions=((0.14, 0.50), (0.26, 0.50), (0.38, 0.50)),
        labels=("Atrás", "Medio", "Adelante"),
    ),
}
