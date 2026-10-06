import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.schemas.club_schemas import ClubUpdate
from app.services import behaviour_service, club_services


@pytest.fixture
def club_repo(monkeypatch):
    repo = Mock()
    monkeypatch.setattr(club_services, "club_repository", repo)
    return repo


def changes():
    return ClubUpdate(name="My club", avatar="avatar-1", friendlyAvailable=True)


def test_club_update_passes_only_validated_fields_and_confirms(db, club_repo):
    club = SimpleNamespace(id=7)
    club_repo.update_club.return_value = club
    assert club_services.update_club(db, club, changes()) is club
    club_repo.update_club.assert_called_once_with(
        db, club, name="My club", avatar="avatar-1", friendly_available=True,
    )
    db.commit.assert_called_once()


def test_duplicate_club_name_is_readable_and_rolls_back(db, club_repo, integrity_error):
    club_repo.update_club.side_effect = integrity_error("clubs_name_key")
    with pytest.raises(AppError) as error:
        club_services.update_club(db, SimpleNamespace(id=7), changes())
    assert error.value.code == "CLUB_NAME_DUPLICATE"
    assert "name" in error.value.fields
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


@pytest.mark.parametrize("source", ["repository", "commit", "unknown_constraint"])
def test_club_update_propagates_unrecognized_failure(db, club_repo, integrity_error, source):
    failure = integrity_error("other") if source == "unknown_constraint" else RuntimeError("failure")
    target = db.commit if source == "commit" else club_repo.update_club
    target.side_effect = failure
    with pytest.raises(type(failure)) as error:
        club_services.update_club(db, SimpleNamespace(id=7), changes())
    assert error.value is failure
    db.rollback.assert_called_once()


def test_joined_leagues_maps_visibility_and_membership_counts(db, club_repo):
    club_repo.get_joined_leagues.return_value = [
        SimpleNamespace(id=1, name="Public", is_private=False, status="open", registrations=[1, 2], max_teams=8),
        SimpleNamespace(id=2, name="Private", is_private=True, status="closed", registrations=[1], max_teams=3),
    ]
    assert club_services.list_joined_leagues(db, 7) == {"items": [
        {"id": 1, "name": "Public", "type": "PUBLIC", "status": "open", "teams": 2, "max_teams": 8},
        {"id": 2, "name": "Private", "type": "PRIVATE", "status": "closed", "teams": 1, "max_teams": 3},
    ]}
    club_repo.get_joined_leagues.assert_called_once_with(db, 7)


def test_behaviour_detail_rejects_missing_or_foreign_behaviour(db, monkeypatch):
    repo = Mock()
    repo.get_behaviour_by_id.return_value = None
    monkeypatch.setattr(behaviour_service, "behaviour_repository", repo)
    with pytest.raises(AppError) as error:
        behaviour_service.behaviour_id(db, 7, 42)
    assert error.value.code == "BEHAVIOUR_NOT_FOUND"
    repo.get_behaviour_by_id.assert_called_once_with(db, 7, 42)


def test_behaviour_list_and_detail_use_current_club(db, monkeypatch):
    behaviour = SimpleNamespace(id=42, name="Custom", code="program")
    repo = Mock()
    repo.get_all_behaviours.return_value = [behaviour]
    repo.get_behaviour_by_id.return_value = behaviour
    monkeypatch.setattr(behaviour_service, "behaviour_repository", repo)
    assert behaviour_service.list_behaviours(db, 7) == [behaviour]
    assert behaviour_service.behaviour_id(db, 7, 42) is behaviour
    repo.get_all_behaviours.assert_called_once_with(db, 7)
    db.commit.assert_not_called()
