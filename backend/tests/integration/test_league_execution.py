"""Rondas completas, recuperación y bloqueos con el motor real y reloj controlado."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import partial
import os
from threading import Barrier, Event
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from test_league_start import database, league_data
from app.errors import AppError
from app.models.behaviour_model import Behavior
from app.models.league_model import League, LeagueRegistration, LeagueRound, LeagueStanding
from app.models.matches_model import Matches
from app.models.team_model import DefaultTeam
from app.repository import league_repository, matches_repository
from app.services import league_execution_service as execution
from app.services import league_service, match_execution_service, match_scheduler_service
from primitives.behaviours import DEFAULT_CODES
from primitives.match_simulation import Match


def registered_lineup(db, club_id):
    lineup = deepcopy(db.get(DefaultTeam, club_id).line_up)
    lineup["starters"].reverse()
    lineup["formationId"] = 2
    return lineup


@pytest.fixture
def running_league(database, league_data, monkeypatch):
    data = league_data
    clock = [datetime(2030, 1, 1, tzinfo=timezone.utc)]

    class Clock:
        @staticmethod
        def now(tz=None):
            return clock[0]

    for service in (league_service, match_scheduler_service, match_execution_service):
        monkeypatch.setattr(service, "datetime", Clock)
    monkeypatch.setattr(match_execution_service, "sleep", lambda _: None)
    monkeypatch.setattr("app.services.match_builder_service.Match",
                        partial(Match, hydration_break_ms=0, half_break_ms=0))
    monkeypatch.setattr(match_scheduler_service, "SessionLocal", sessionmaker(database))
    if database.dialect.name == "postgresql":
        # En PostgreSQL se usa el advisory lock real del ejecutor.
        monkeypatch.setattr(matches_repository, "engine", database)
    else:
        @contextmanager
        def execution_session(match_id):
            with Session(database, expire_on_commit=False) as db:
                yield db
        monkeypatch.setattr(matches_repository, "execution_session", execution_session)

    with Session(database) as db:
        for behaviour in db.scalars(select(Behavior)):
            behaviour.code = DEFAULT_CODES["Equilibrado"]
        league = db.get(League, data.id)
        league.round_interval = "CONTINUOUS"
        # Un orden distinto del catálogo permite detectar selección de jugadores incorrecta.
        for registration in league.registrations:
            registration.line_up = registered_lineup(db, registration.club_id)
        db.commit()
    return data, clock


def start(db, data, count=3):
    if count == 4:
        db.add(LeagueRegistration(
            league_id=data.id, club_id=data.clubs[3],
            line_up=registered_lineup(db, data.clubs[3]),
        ))
        db.commit()
    league_service.start_league(db, data.id, data.clubs[0])
    for match in league_repository.get_fixture_matches(db, data.id):
        match.duration_ms = 300
    db.commit()


@pytest.mark.parametrize("count", [3, 4])
def test_scheduler_finishes_all_rounds_offline_and_resumes_saved_match(database, running_league, count):
    data, clock = running_league
    with Session(database) as db:
        start(db, data, count)

    for round_number in range(1, 4):
        # Es el mismo polling que ejecuta el scheduler; no hay acciones de usuarios.
        ids = match_scheduler_service._get_due_match_ids()
        assert len(ids) == count // 2
        with Session(database) as db:
            current = [db.get(Matches, id_) for id_ in ids]
            assert all(match.status == "RUNNING" for match in current)
            assert all(match.started_at.replace(tzinfo=timezone.utc) == clock[0] for match in current)
            assert len({match.league_round_id for match in current}) == 1
            clubs = [id_ for match in current for id_ in (match.creator_id, match.visitor_id)]
            assert len(clubs) == len(set(clubs))
            round_ = db.get(LeagueRound, current[0].league_round_id)
            assert round_.number == round_number
            assert round_.scheduled_at.replace(tzinfo=timezone.utc) == clock[0]
            assert all(match.init_date == round_.scheduled_at for match in current)
            assert not db.scalars(select(Matches).where(Matches.league_round_id != round_.id,
                                                        Matches.status == "RUNNING")).all()

        if round_number == 1:
            stop = Mock(spec=Event)
            stop.is_set.return_value = False
            stop.wait.side_effect = [False, True]
            partial = match_execution_service.run_persisted_match(ids[0], stop_event=stop)
            assert 0 < partial["state"]["clockMs"] < 300
            with Session(database) as db:
                row = db.get(Matches, ids[0])
                assert row.runtime_state["local_team"]["formation_id"] == 2
                assert all(p["behaviour_version"] == 1 for p in row.runtime_state["local_team"]["players"])
                captured_players = [player["id"] for player in row.snapshot["state"]["players"]]
                registration = league_repository.get_registration(db, data.id, row.creator_id)
                expected = [selection["playerId"] for selection in registration.line_up["starters"]]
                assert captured_players[:len(expected)] == expected
                original = deepcopy(registration.line_up)
                # Un reinicio debe conservar el checkpoint aunque la alineación ya haya cambiado.
                registration.line_up = []
                db.commit()
            assert set(ids).issubset(match_scheduler_service._get_due_match_ids())
            final = match_execution_service.run_persisted_match(ids[0])
            assert final["sequence"] > partial["sequence"]
            assert [player["id"] for player in final["state"]["players"]] == captured_players
            with Session(database) as db:
                registration = league_repository.get_registration(db, data.id, current[0].creator_id)
                registration.line_up = original
                db.commit()

        for id_ in ids:
            final = match_execution_service.run_persisted_match(id_)
            assert final["state"]["status"] == "FINISHED"
            # Repetir la ejecución devuelve lo ya persistido, sin nuevas secuencias.
            assert match_execution_service.run_persisted_match(id_) == final

        with Session(database) as db:
            league = db.get(League, data.id)
            if round_number < 3:
                assert league.status == "running"
                next_round = db.scalar(select(LeagueRound).where(
                    LeagueRound.league_id == data.id, LeagueRound.number == round_number + 1,
                ))
                assert next_round.schedule_confirmed
                assert next_round.scheduled_at.replace(tzinfo=timezone.utc) == clock[0] + timedelta(seconds=360)
                assert match_scheduler_service._get_due_match_ids() == []
            else:
                assert league.status == "finished"
        clock[0] += timedelta(seconds=360)

    assert match_scheduler_service._get_due_match_ids() == []
    with Session(database) as db:
        matches = league_repository.get_fixture_matches(db, data.id)
        assert len(matches) == count * (count - 1) // 2
        assert all(match.status == "FINISHED" and match.finished_at for match in matches)
        assert len(db.scalars(select(LeagueStanding)).all()) == count
        ranking = league_service.league_rank(data.id, db)
        assert all(row["pj"] == count - 1 for row in ranking)


def test_league_captures_custom_behaviour_source_and_version(database, running_league):
    data, _ = running_league
    source = "def decide(observation):\n    return ir_a_pelota()\n"
    with Session(database) as db:
        for behaviour in db.scalars(select(Behavior)):
            behaviour.code = source
            behaviour.version = 4
        db.commit()
        start(db, data)

    ids = match_scheduler_service._get_due_match_ids()
    assert len(ids) == 1
    with Session(database) as db:
        row = db.get(Matches, ids[0])
        players = row.runtime_state["local_team"]["players"]
        assert all(player["behaviour_code"] == source for player in players)
        assert all(player["behaviour_version"] == 4 for player in players)
    assert match_execution_service.run_persisted_match(ids[0])["state"]["status"] == "FINISHED"


def test_busy_club_delays_whole_round_without_cancelling_matches(database, running_league):
    data, clock = running_league
    with Session(database) as db:
        start(db, data, 4)
        first = league_repository.get_fixture_matches(db, data.id)[0]
        busy = Matches(creator_id=first.creator_id, visitor_id=first.visitor_id,
                       init_date=clock[0], status="RUNNING")
        db.add(busy)
        db.commit()
        busy_id = busy.match_id
        assert execution.get_due_league_match_ids(db, clock[0]) == []

    with Session(database) as db:
        matches = league_repository.get_fixture_matches(db, data.id)
        assert all(match.status == "SCHEDULED" and match.snapshot is None for match in matches)
        busy = db.get(Matches, busy_id)
        busy.status, busy.cancellation_reason = "CANCELLED", "TEST_RELEASE"
        db.commit()
        clock[0] += timedelta(seconds=30)
        ids = execution.get_due_league_match_ids(db, clock[0])
        assert len(ids) == 2
        assert all(db.get(Matches, id_).started_at.replace(tzinfo=timezone.utc) == clock[0] for id_ in ids)


def test_invalid_second_match_rolls_back_entire_round(database, running_league, monkeypatch):
    data, clock = running_league
    with Session(database) as db:
        start(db, data, 4)
        builder = execution.build_match
        calls = []

        def fail_second(db, match_id, **kwargs):
            calls.append(match_id)
            if len(calls) == 2:
                raise RuntimeError("Error simulado")
            return builder(db, match_id, **kwargs)

        monkeypatch.setattr(execution, "build_match", fail_second)
        with pytest.raises(RuntimeError, match="Error simulado"):
            execution.prepare_league_round(db, data.id, clock[0])
    with Session(database) as db:
        matches = league_repository.get_fixture_matches(db, data.id)
        assert all(match.status == "SCHEDULED" and match.runtime_state is None for match in matches)
        monkeypatch.setattr(execution, "build_match", builder)
        assert len(execution.prepare_league_round(db, data.id, clock[0])) == 2


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
def test_two_schedulers_prepare_round_once(database, running_league):
    data, clock = running_league
    with Session(database) as db:
        start(db, data, 4)
    barrier = Barrier(2)

    def prepare(_):
        with Session(database) as db:
            barrier.wait(timeout=5)
            return execution.prepare_league_round(db, data.id, clock[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(prepare, range(2)))
    assert first == second
    assert len(first) == 2
    with Session(database) as db:
        assert all(db.get(Matches, id_).sequence == 1 for id_ in first)
        assert len(league_repository.get_fixture_matches(db, data.id)) == 6


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
def test_overlapping_leagues_cannot_start_same_clubs_together(database, running_league):
    data, clock = running_league
    with Session(database) as db:
        start(db, data, 4)
        other = League(
            name="Otra liga", creator_club_id=data.clubs[0], min_teams=3, max_teams=4,
            start_datetime=clock[0], round_interval="CONTINUOUS",
            registrations=[LeagueRegistration(
                club_id=id_, line_up=deepcopy(db.get(DefaultTeam, id_).line_up),
            ) for id_ in data.clubs],
        )
        db.add(other)
        db.commit()
        other_id = other.id
        league_service.start_league(db, other_id, data.clubs[0])
    barrier = Barrier(2)

    def prepare(league_id):
        with Session(database) as db:
            barrier.wait(timeout=5)
            return execution.prepare_league_round(db, league_id, clock[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(prepare, [data.id, other_id]))
    assert sorted(map(len, results)) == [0, 2]
    with Session(database) as db:
        running = db.scalars(select(Matches).where(Matches.status == "RUNNING")).all()
        clubs = [id_ for match in running for id_ in (match.creator_id, match.visitor_id)]
        assert len(clubs) == len(set(clubs)) == 4
        assert not db.scalars(select(Matches).where(Matches.status == "CANCELLED")).all()


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
def test_confirmed_league_round_has_priority_over_concurrent_friendly(database, running_league):
    data, clock = running_league
    with Session(database) as db:
        start(db, data, 4)
        round_ = league_repository.get_fixture_rounds(db, data.id)[0]
        assert round_.schedule_confirmed
        first, second = league_repository.get_round_matches_for_update(db, round_.id)
        round_match_ids = {first.match_id, second.match_id}
        friendly = Matches(
            creator_id=first.creator_id,
            visitor_id=second.creator_id,
            init_date=round_.scheduled_at,
            status="SCHEDULED",
        )
        db.add(friendly)
        db.flush()
        friendly_id = friendly.match_id
        db.commit()
    barrier = Barrier(2)

    def prepare_round():
        with Session(database) as db:
            barrier.wait(timeout=5)
            return execution.prepare_league_round(db, data.id, clock[0])

    def start_friendly():
        barrier.wait(timeout=5)
        return match_execution_service.run_persisted_match(friendly_id, duration_ms=300)

    with ThreadPoolExecutor(max_workers=2) as pool:
        league_result = pool.submit(prepare_round)
        friendly_result = pool.submit(start_friendly)
        assert set(league_result.result(timeout=10)) == round_match_ids
        snapshot = friendly_result.result(timeout=10)
        assert snapshot["state"]["status"] == "CANCELLED"
        assert snapshot["state"]["cancellationReason"] == "LEAGUE_SCHEDULE_CONFLICT"

    with Session(database) as db:
        friendly = db.get(Matches, friendly_id)
        assert (friendly.status, friendly.cancellation_reason) == ("CANCELLED", "LEAGUE_SCHEDULE_CONFLICT")
        assert friendly.started_at is None
        for match_id in round_match_ids:
            match = db.get(Matches, match_id)
            assert match.status == "RUNNING"
            assert match.started_at == clock[0]


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
def test_league_writer_lock_survives_commits_and_allows_resume_after_release(database, running_league):
    data, clock = running_league
    with Session(database) as db:
        start(db, data)
        match_id = execution.prepare_league_round(db, data.id, clock[0])[0]

    # Simula otro backend que conserva el writer lock entre snapshots.
    with matches_repository.execution_session(match_id) as owner:
        owner.commit()
        with ThreadPoolExecutor(max_workers=1) as pool:
            duplicate = pool.submit(match_execution_service.run_persisted_match, match_id)
            with pytest.raises(AppError) as error:
                duplicate.result(timeout=10)
        assert error.value.code == "MATCH_ALREADY_RUNNING"

    assert match_execution_service.run_persisted_match(match_id)["state"]["status"] == "FINISHED"
