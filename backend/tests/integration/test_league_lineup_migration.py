from copy import deepcopy

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.migrate_league_lineups import migrate_league_lineups
from app.models.league_model import League
from app.models.team_model import DefaultTeam
from app.repository import league_repository
from app.services import league_execution_service, league_service
from app.services.league_lineup_service import INCOMPLETE_LEGACY_LINEUP
from test_league_start import database, league_data


def test_migrates_verified_lineups_and_requires_open_league_to_fix_ambiguous_registration(database, league_data):
    data = league_data
    creator, member, ambiguous = data.clubs[:3]
    with Session(database) as db:
        registration = league_repository.get_registration(db, data.id, ambiguous)
        original_ids = list(reversed(registration.line_up))
        registration.line_up = original_ids
        db.commit()

        assert migrate_league_lineups(db) == (2, 1)
        assert migrate_league_lineups(db) == (0, 0)
        for club_id in (creator, member):
            verified = league_repository.get_registration(db, data.id, club_id)
            assert verified.line_up == db.get(DefaultTeam, club_id).line_up
        assert registration.line_up == {
            "status": INCOMPLETE_LEGACY_LINEUP, "legacyPlayerIds": original_ids,
        }

        with pytest.raises(HTTPException, match=f"club #{ambiguous}") as error:
            league_service.start_league(db, data.id, creator)
        assert error.value.status_code == 409
        assert db.get(League, data.id).status == "open"
        assert league_repository.get_fixture_matches(db, data.id) == []

        league_service.leave_league(db, data.id, ambiguous)
        league_service.join_league(db, data.id, ambiguous, data.lineups[2])
        assert league_service.start_league(db, data.id, creator)["status"] == "running"


def test_legacy_creator_can_fix_its_default_team_and_start(database, league_data):
    data = league_data
    creator = data.clubs[0]
    with Session(database) as db:
        team = db.get(DefaultTeam, creator)
        valid = deepcopy(team.line_up)
        team.line_up = {**valid, "formationId": 9999}
        db.commit()

        assert migrate_league_lineups(db) == (2, 1)
        registration = league_repository.get_registration(db, data.id, creator)
        assert registration.line_up["status"] == INCOMPLETE_LEGACY_LINEUP
        with pytest.raises(HTTPException, match="equipo predeterminado"):
            league_service.start_league(db, data.id, creator)

        team.line_up = valid
        db.commit()
        assert league_service.start_league(db, data.id, creator)["status"] == "running"
        assert registration.line_up == valid


def test_running_league_can_resume_with_previous_legacy_order(database, league_data):
    data = league_data
    with Session(database) as db:
        league_service.start_league(db, data.id, data.clubs[0])
        first_round = league_repository.get_fixture_rounds(db, data.id)[0]
        first_match = league_repository.get_round_matches_for_update(db, first_round.id)[0]
        club_id = first_match.creator_id
        registration = league_repository.get_registration(db, data.id, club_id)
        default = db.get(DefaultTeam, club_id).line_up
        ids = [slot["playerId"] for slot in default["starters"] + default["substitutes"]]
        registration.line_up = list(reversed(ids))
        db.commit()

        assert migrate_league_lineups(db) == (0, 0)
        assert isinstance(registration.line_up, list)
        assert league_execution_service.prepare_league_round(db, data.id, first_round.scheduled_at)
        assert registration.line_up == default
