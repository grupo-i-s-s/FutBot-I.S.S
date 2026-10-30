import pytest
from fastapi import HTTPException
from types import SimpleNamespace
from unittest.mock import Mock

from app.controller import league_controller
from app.schemas.league_schemas import LeagueJoinRequest


def test_league_join_rejects_spoofed_club_before_calling_service(db, monkeypatch):
    join = Mock()
    monkeypatch.setattr(league_controller.league_service, "join_league", join)
    body = LeagueJoinRequest(clubId=999, lineUp=[1, 2, 3, 4, 5, 6])
    with pytest.raises(HTTPException) as error:
        league_controller.join_league(42, body, SimpleNamespace(id=7), db)
    assert error.value.status_code == 403
    join.assert_not_called()


def test_league_join_forwards_selected_lineup_and_access_code(db, monkeypatch):
    join = Mock(return_value={"leagueId": 42})
    monkeypatch.setattr(league_controller.league_service, "join_league", join)
    body = LeagueJoinRequest(clubId=7, lineUp=[6, 5, 4, 3, 2, 1], accessCode="secret")
    assert league_controller.join_league(42, body, SimpleNamespace(id=7), db) == {"leagueId": 42}
    join.assert_called_once_with(db=db, league_id=42, club_id=7,
                                 line_up=[6, 5, 4, 3, 2, 1], access_code="secret")
