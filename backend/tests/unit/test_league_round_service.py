from itertools import combinations
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import league_round_service as service


@pytest.mark.parametrize("club_count", [3, 4, 5, 6])
def test_rounds_cover_every_pair_and_each_club_once_per_round(club_count):
    club_ids = list(range(1, club_count + 1))
    rounds = service.generate_rounds(club_ids, seed=42)
    expected_round_count = club_count if club_count % 2 else club_count - 1

    assert [round_.number for round_ in rounds] == list(
        range(1, expected_round_count + 1)
    )

    all_pairings = []
    rests = []
    for round_ in rounds:
        playing_clubs = []
        assert len(round_.pairings) == club_count // 2
        for home_id, away_id in round_.pairings:
            assert home_id != away_id
            playing_clubs.extend([home_id, away_id])
            all_pairings.append(tuple(sorted((home_id, away_id))))

        assert len(playing_clubs) == len(set(playing_clubs))
        if club_count % 2:
            assert round_.bye_club_id not in playing_clubs
            rests.append(round_.bye_club_id)
            playing_clubs.append(round_.bye_club_id)
        else:
            assert round_.bye_club_id is None
        assert set(playing_clubs) == set(club_ids)

    assert len(all_pairings) == club_count * (club_count - 1) // 2
    assert set(all_pairings) == set(combinations(club_ids, 2))
    if club_count % 2:
        assert sorted(rests) == club_ids


def test_same_seed_reproduces_draw_without_changing_input():
    club_ids = [5, 1, 3, 2, 4]
    original = club_ids.copy()

    rounds = service.generate_rounds(club_ids, seed=42)

    assert rounds == service.generate_rounds(list(reversed(club_ids)), seed=42)
    assert club_ids == original


@pytest.mark.parametrize("club_ids, seed", [
    ([1, 2], 42),
    ([1, 2, 2], 42),
    ([0, 2, 3], 42),
    ([True, 2, 3], 42),
    (["1", 2, 3], 42),
    ((1, 2, 3), 42),
    ([1, 2, 3], "42"),
])
def test_invalid_participants_or_seed_are_rejected(club_ids, seed):
    with pytest.raises(ValueError):
        service.generate_rounds(club_ids, seed=seed)


@pytest.mark.parametrize("saved_seed", [None, 0, 42])
def test_league_generates_seed_once_and_reuses_saved_seed(db, monkeypatch, saved_seed):
    new_seed = Mock(return_value=123)
    monkeypatch.setattr(service.secrets, "randbits", new_seed)
    league = SimpleNamespace(
        draw_seed=saved_seed,
        registrations=[SimpleNamespace(club_id=id_) for id_ in [1, 2, 3, 4]],
    )

    rounds = service.generate_league_rounds(db, league)
    seed = 123 if saved_seed is None else saved_seed

    assert league.draw_seed == seed
    assert rounds == service.generate_rounds([1, 2, 3, 4], seed=seed)
    db.flush.assert_called_once()
    db.commit.assert_not_called()

    league.registrations.reverse()
    assert service.generate_league_rounds(db, league) == rounds
    if saved_seed is None:
        new_seed.assert_called_once_with(63)
    else:
        new_seed.assert_not_called()


def test_invalid_league_does_not_save_seed(db):
    league = SimpleNamespace(
        draw_seed=None,
        registrations=[SimpleNamespace(club_id=1)],
    )

    with pytest.raises(ValueError):
        service.generate_league_rounds(db, league)

    assert league.draw_seed is None
    db.flush.assert_not_called()
