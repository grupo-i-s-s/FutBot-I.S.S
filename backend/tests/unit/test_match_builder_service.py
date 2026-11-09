import pytest
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.services import match_builder_service as service
from primitives.behaviour_api.registry import API_VERSION
from primitives.behaviours import BehaviourMode, DEFAULT_CODES, LEGACY_CODE
from primitives.match_simulation import Match


@pytest.fixture
def teams(monkeypatch):
    players = {}
    behaviours = {}
    lineups = {}
    for club_id in (7, 9):
        players[club_id] = [
            SimpleNamespace(
                id=club_id * 10 + index, club_id=club_id,
                name=f"Jugador {club_id}-{index}", speed=40 + index * 4, power=60,
                agility=50 + index * 2, strength=80 - index * 4, control=70 - index * 2,
                behavior_id=club_id * 100,
            )
            for index in range(6)
        ]
        behaviours[club_id] = [
            SimpleNamespace(
                id=club_id * 100 + index, club_id=club_id,
                name=name, code=DEFAULT_CODES[name],
                kind="PLAYER", version=1, validation_status="VALID",
            )
            for index, name in enumerate(("Equilibrado", "Ofensivo", "Defensivo"))
        ]
        lineups[club_id] = {
            "formationId": 2 if club_id == 7 else 3,
            "starters": [
                {"playerId": club_id * 10 + index, "behaviourId": club_id * 100 + mode}
                for index, mode in ((4, 2), (0, 0), (2, 1))
            ],
            "substitutes": [
                {"playerId": club_id * 10 + index, "behaviourId": club_id * 100}
                for index in (1, 3, 5)
            ],
        }

    matches = Mock()
    matches.get_by_id.return_value = SimpleNamespace(
        creator_id=7, visitor_id=9, duration_ms=300_000,
    )
    matches.get_club_names.return_value = {7: "Local", 9: "Visitante"}
    matches.get_club_avatars.return_value = {7: "avatar-07.png", 9: "avatar-09.png"}
    saved = Mock()
    saved.get_by_club.side_effect = lambda db, cid: SimpleNamespace(line_up=lineups[cid])
    player_repo = Mock()
    player_repo.get_players_by_club.side_effect = lambda db, cid: players[cid]
    behaviour_repo = Mock()
    behaviour_repo.get_all_behaviours.side_effect = lambda db, cid: behaviours[cid]
    monkeypatch.setattr(service, "matches_repository", matches)
    monkeypatch.setattr(service, "team_repository", saved)
    monkeypatch.setattr(service, "player_repository", player_repo)
    monkeypatch.setattr(service, "behaviour_repository", behaviour_repo)
    return SimpleNamespace(
        players=players, behaviours=behaviours, lineups=lineups,
        matches=matches, saved=saved,
    )


def test_builder_uses_saved_starter_order_formation_and_slot_behaviours(db, teams):
    match = service.build_match(db, 42)

    assert match.match_id == 42
    assert [player.id for player in match.player_profiles] == [74, 70, 72, 94, 90, 92]
    assert [player.club_id for player in match.player_profiles] == [7, 7, 7, 9, 9, 9]
    assert [player.behaviour_id for player in match.local_team.players] == [702, 700, 701]
    assert [player.behaviour_mode for player in match.local_team.players] == [
        BehaviourMode.DEFENSIVE, BehaviourMode.BALANCED, BehaviourMode.OFFENSIVE,
    ]
    assert match.local_team.formation_id == 2
    assert match.visitor_team.formation_id == 3
    assert match.local_team.avatar == "avatar-07.png"
    assert match.visitor_team.avatar == "avatar-09.png"
    assert match.home_positions[74] == pytest.approx((18, 30))
    assert match.home_positions[94] == pytest.approx((86, 30))
    assert match.player_bodies[74] is match.world.players[0]
    assert match.player_bodies[92] is match.world.players[5]
    source_players = {
        player.id: player
        for roster in teams.players.values()
        for player in roster
    }
    for profile in match.player_profiles:
        original = source_players[profile.id]
        for attribute in ("power", "agility", "control", "speed", "strength"):
            assert getattr(profile, attribute) == getattr(original, attribute)
        assert match.player_bodies[profile.id].mass == pytest.approx(profile.real_strength)
    teams.matches.get_starting_players.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("invalid", ["missing", "malformed", "incomplete", "duplicate", "formation"])
def test_builder_rejects_invalid_saved_lineup(db, teams, invalid):
    if invalid == "missing":
        teams.saved.get_by_club.side_effect = lambda *_: None
    elif invalid == "malformed":
        teams.lineups[7] = []
    elif invalid == "incomplete":
        teams.lineups[7]["starters"].pop()
    elif invalid == "duplicate":
        teams.lineups[7]["starters"][0] = teams.lineups[7]["substitutes"][0]
    else:
        teams.lineups[7]["formationId"] = 999

    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == "MATCH_INVALID_LINEUP"
    db.commit.assert_not_called()


@pytest.mark.parametrize("unavailable", ["player", "behaviour"])
def test_builder_rejects_deleted_or_foreign_selections(db, teams, unavailable):
    field = "playerId" if unavailable == "player" else "behaviourId"
    # An otherwise existing ID belonging to the opponent must also be rejected.
    teams.lineups[7]["starters"][0][field] = 94 if unavailable == "player" else 902
    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == "MATCH_INVALID_LINEUP"


def test_builder_freezes_configuration_and_supports_legacy_behaviours(db, teams):
    teams.behaviours[7][2].code = LEGACY_CODE
    match = service.build_match(db, 42)
    teams.behaviours[7][2].code = DEFAULT_CODES["Ofensivo"]
    teams.lineups[7]["formationId"] = 1

    assert match.local_team.players[0].behaviour_mode == BehaviourMode.DEFENSIVE
    assert match.local_team.formation_id == 2
    assert service.build_match(db, 43).local_team.formation_id == 1


def test_builder_rejects_unsupported_behaviour_code(db, teams):
    teams.behaviours[7][2].code = "raise RuntimeError('no ejecutar')"
    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == "MATCH_INVALID_BEHAVIOUR"


@pytest.mark.parametrize("club_id", [7, 9])
def test_builder_accepts_custom_behaviour_and_freezes_source_and_version(db, teams, club_id):
    source = "def decide(observation):\n    return ir_a_pelota()\n"
    behaviour = teams.behaviours[club_id][2]
    behaviour.name = "Perseguir pelota"
    behaviour.code = source
    behaviour.version = 4

    match = service.build_match(db, 42)
    player_id = club_id * 10 + 4
    profile = next(player for player in match.player_profiles if player.id == player_id)

    assert profile.club_id == club_id
    assert profile.behaviour_id == behaviour.id
    assert profile.behaviour_code == source
    assert profile.behaviour_version == 4
    assert profile.behaviour_api_version == API_VERSION

    updated_source = "def decide(observation):\n    return ir_a(posicion_base())\n"
    behaviour.code = updated_source
    behaviour.version = 5
    updated_match = service.build_match(db, 43)
    updated_profile = next(
        player for player in updated_match.player_profiles if player.id == player_id
    )

    assert profile.behaviour_code == source
    assert profile.behaviour_version == 4
    assert updated_profile.behaviour_code == updated_source
    assert updated_profile.behaviour_version == 5
    db.commit.assert_not_called()


@pytest.mark.parametrize("kind, validation_status", [
    ("PLAYER", "INVALID"),
    ("PLAYER", "PENDING"),
    ("COACH", "VALID"),
])
def test_builder_rejects_custom_behaviour_that_is_not_valid_player(
    db, teams, kind, validation_status,
):
    behaviour = teams.behaviours[7][2]
    behaviour.code = "def decide(observation):\n    return ir_a_pelota()\n"
    behaviour.kind = kind
    behaviour.validation_status = validation_status

    with pytest.raises(AppError) as error:
        service.build_match(db, 42)

    assert error.value.code == "MATCH_INVALID_BEHAVIOUR"
    db.commit.assert_not_called()


def test_builder_rejects_custom_behaviour_from_opponent_club(db, teams):
    foreign_behaviour = teams.behaviours[9][2]
    foreign_behaviour.code = "def decide(observation):\n    return ir_a_pelota()\n"
    teams.lineups[7]["starters"][0]["behaviourId"] = foreign_behaviour.id

    with pytest.raises(AppError) as error:
        service.build_match(db, 42)

    assert error.value.code == "MATCH_INVALID_LINEUP"
    db.commit.assert_not_called()


@pytest.mark.parametrize("missing, code", [("match", "MATCH_NOT_FOUND"), ("visitor", "MATCH_NO_VISITOR")])
def test_missing_match_or_opponent_is_rejected_before_loading_teams(db, teams, missing, code):
    teams.matches.get_by_id.return_value = (
        None if missing == "match" else SimpleNamespace(visitor_id=None)
    )
    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == code
    teams.saved.get_by_club.assert_not_called()


def test_builder_captures_both_benches_without_putting_them_on_field(db, teams):
    match = service.build_match(db, 42)
    assert [p.id for p in match.local_team.substitutes] == [71, 73, 75]
    assert [p.id for p in match.visitor_team.substitutes] == [91, 93, 95]
    assert [p.behaviour_id for p in match.local_team.substitutes] == [700, 700, 700]
    assert len(match.world.players) == 6
    assert set(match.player_bodies) == {74, 70, 72, 94, 90, 92}


def test_bench_configuration_is_frozen_and_recovers_from_json_checkpoint(db, teams):
    source = "def decide(observation):\n    return ir_a_pelota()\n"
    teams.behaviours[7][0].code = source
    teams.behaviours[7][0].version = 4
    match = service.build_match(db, 42)
    checkpoint = json.loads(json.dumps(match.checkpoint()))
    teams.behaviours[7][0].code = DEFAULT_CODES["Ofensivo"]
    teams.behaviours[7][0].version = 5
    teams.lineups[7]["substitutes"].reverse()
    teams.players[7][1].name = "Nombre nuevo"

    restored = Match.from_checkpoint(checkpoint)
    assert checkpoint["version"] == 5
    assert restored.local_team.substitutes == match.local_team.substitutes
    assert restored.visitor_team.substitutes == match.visitor_team.substitutes
    assert [p.id for p in restored.local_team.substitutes] == [71, 73, 75]
    assert all(p.behaviour_code == source and p.behaviour_version == 4
               for p in restored.local_team.substitutes)
    assert restored.local_team.substitutes[0].name == "Jugador 7-1"
    assert json.loads(json.dumps(restored.checkpoint())) == checkpoint


def test_legacy_checkpoint_recovers_without_inventing_a_bench(db, teams):
    checkpoint = json.loads(json.dumps(service.build_match(db, 42).checkpoint()))
    checkpoint["version"] = 4
    for key in ("local_team", "visitor_team"):
        del checkpoint[key]["substitutes"]
    restored = Match.from_checkpoint(checkpoint)
    assert restored.local_team.substitutes == ()
    assert restored.visitor_team.substitutes == ()
    assert [p.id for p in restored.player_profiles] == [74, 70, 72, 94, 90, 92]


@pytest.mark.parametrize("field, foreign_id", [("playerId", 91), ("behaviourId", 900)])
def test_builder_rejects_a_bench_selection_from_the_other_club(db, teams, field, foreign_id):
    teams.lineups[7]["substitutes"][0][field] = foreign_id
    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == "MATCH_INVALID_LINEUP"


def test_league_bench_comes_from_its_registration_not_the_default_team(db, teams):
    lineups = deepcopy(teams.lineups)
    lineups[7]["substitutes"].reverse()
    registrations = {club_id: SimpleNamespace(line_up=lineup) for club_id, lineup in lineups.items()}
    match = service.build_match(db, 42, league_teams=registrations)
    assert [p.id for p in match.local_team.substitutes] == [75, 73, 71]
    teams.saved.get_by_club.assert_not_called()
