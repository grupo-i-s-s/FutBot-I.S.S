import hashlib
from collections.abc import Callable
from typing import Any

from primitives.behaviour_api.actions import Actions
from primitives.behaviour_api.queries import DtQueries, Queries
from primitives.behaviours import BehaviourMode


API_VERSION = 1

RegisteredFunction = Callable[..., Any]
Registry = dict[str, RegisteredFunction]


def program_key(source: str, kind: str) -> str:
    return hashlib.sha256(f"{API_VERSION}\0{kind}\0{source}".encode("utf-8")).hexdigest()


# Nombre público en español -> nombre interno en inglés.
QUERY_METHODS = {
    "tiempo_jugado": "played_time",
    "tiempo_restante": "remaining_time",
    "vamos_ganando": "winning",
    "vamos_empatando": "drawing",
    "tengo_pelota": "ball_possession",
    "equipo_tiene_pelota": "team_has_possession",
    "estamos_atacando": "attacking",
    "estamos_defendiendo": "defending",
    "bajo_presion": "under_pressure",
    "pelota_en_nuestro_campo": "ball_on_our_side",
    "pelota_en_su_campo": "ball_on_their_side",
    "pelota_libre": "loose_ball",
    "puedo_patear": "can_kick",
    "mi_posicion": "my_position",
    "posicion_pelota": "ball_position",
    "posicion_base": "base_position",
    "arco_propio": "our_goal",
    "arco_rival": "their_goal",
    "compañeros": "teammates",
    "rivales": "opponents",
    "compañero_mas_cercano": "closer_teammate",
    "rival_mas_cercano": "closest_opponent",
}

DT_QUERY_METHODS = {
    "vamos_ganando": "winning",
    "vamos_empatando": "drawing",
    "vamos_perdiendo": "losing",
    "tiempo_jugado": "time_played",
    "perdiendo_por": "losing_by",
    "ganando_por": "winning_by",
}


ACTION_METHODS = {
    "patear_a": "kick_to",
    "ir_a": "go_to",
    "ir_a_pelota": "go_to_ball",
    "quedarse": "stay",
    "cubrir_arco": "cover_goal",
    "conducir_hacia": "dribble_to",
}


# Parámetro público en español -> parámetro interno en inglés.
ACTION_PARAMETERS = {
    "patear_a": {
        "direccion": "direction",
    },
    "ir_a": {
        "direccion": "direction",
    },
    "ir_a_pelota": {},
    "quedarse": {
        "posicion": "position",
    },
    "cubrir_arco": {},
    "conducir_hacia": {
        "direccion": "direction",
    },
}


QUERY_NAMES = frozenset(QUERY_METHODS)
ACTION_NAMES = frozenset(ACTION_METHODS)


def _expose_action(method: RegisteredFunction, parameter_names: dict[str, str]) -> RegisteredFunction:

    def execute(*args, **kwargs):
        translated_kwargs = {}

        for public_name, value in kwargs.items():
            if public_name not in parameter_names:
                raise TypeError(f"Parámetro no reconocido: {public_name}.")

            internal_name = parameter_names[public_name]
            translated_kwargs[internal_name] = value

        return method(*args, **translated_kwargs)

    return execute


def build_registry(queries: Queries) -> tuple[Registry, Registry]:

    actions = Actions(queries)

    query_registry: Registry = {
        public_name: getattr(queries, internal_name)
        for public_name, internal_name in QUERY_METHODS.items()
    }

    action_registry: Registry = {
        public_name: _expose_action(
            getattr(actions, internal_name),
            ACTION_PARAMETERS[public_name],
        )
        for public_name, internal_name in ACTION_METHODS.items()
    }

    return query_registry, action_registry

def build_dt_registry(queries: DtQueries) -> Registry:
    def cambiar_comportamiento(jugador_id: int, modo: BehaviourMode) -> dict:
        return {"player_id": jugador_id, "mode": modo}

    def sustituir(saliente_id: int, entrante_id: int) -> dict:
        return {"outgoing_player_id": saliente_id, "incoming_player_id": entrante_id}

    return {
        **{
            public_name: getattr(queries, internal_name)
            for public_name, internal_name in DT_QUERY_METHODS.items()
        },
        "cambiar_comportamiento": cambiar_comportamiento,
        "sustituir": sustituir,
    }
