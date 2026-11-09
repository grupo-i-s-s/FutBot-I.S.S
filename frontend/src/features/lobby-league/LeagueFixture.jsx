import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {buttonVariants} from '@/components/ui/button';
import {routePath, routes} from '@/routes.js';
import {obtenerFixture} from './api.js';

const states = {
    WAITING: 'Pendiente', WAITING_OPPONENT: 'Pendiente', SCHEDULED: 'Pendiente',
    RUNNING: 'En juego', FINISHED: 'Finalizado', CANCELLED: 'Cancelado',
};

function MatchDate({round}) {
    return <p>
        <time dateTime={round.scheduledAt}>{new Date(round.scheduledAt).toLocaleString('es-AR')}</time>
        {!round.scheduleConfirmed && ' (Horario previsto)'}
    </p>;
}

export default function LeagueFixture({id, clubId, clubs, leagueStatus, isRegistered, refresh, onRefresh}) {
    const [fixture, setFixture] = useState(null);
    const [selectedRound, setSelectedRound] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        const controller = new AbortController();
        setError(null);
        obtenerFixture(id, controller.signal).then(data => {
            if (controller.signal.aborted) return;
            setFixture(data);
            setSelectedRound(current => data.rounds.some(round => round.number === current)
                ? current : data.nextMatch?.roundNumber ?? data.rounds[0]?.number ?? null);
        }).catch(err => {
            if (!controller.signal.aborted) setError(err);
        });
        return () => controller.abort();
    }, [id, refresh]);

    if (!fixture) return <section className="lobby-card" aria-label="Fixture">
        <h2>Fixture</h2>
        {error ? <><p role="alert">{error.message}</p><button type="button" onClick={onRefresh}>Reintentar fixture</button></>
            : <p role="status">Cargando fixture…</p>}
    </section>;

    const round = fixture.rounds.find(round => round.number === selectedRound);
    const next = fixture.nextMatch;
    const activeRound = fixture.rounds.find(round => round.matches.some(match => match.status === 'RUNNING'))
        ?? fixture.rounds.find(round => round.matches.some(match => states[match.status] === 'Pendiente'));
    const playing = fixture.rounds.some(round => round.matches.some(match =>
        match.status === 'RUNNING' && [match.creatorClubId, match.visitorClubId].includes(clubId)));

    return <section className="lobby-card" aria-label="Fixture">
        <h2>Fixture</h2>
        {error && <p role="alert">{error.message}</p>}
        {leagueStatus === 'finished' ? <p>La liga finalizó.</p> : <>
            {activeRound?.byeClubId === clubId && <p>Tu club descansa en la ronda {activeRound.number}.</p>}
            {next ? <div className="league-next-match">
                <h3>Tu próximo partido</h3>
                <p>Ronda {next.roundNumber}: contra {next.creatorClubId === clubId ? next.visitorClubName : next.creatorClubName}.</p>
                <MatchDate round={next}/>
            </div> : <p>{!isRegistered ? 'Tu club no participa en esta liga.'
                : playing ? 'Tu club está jugando.' : 'Tu club ya no tiene partidos pendientes.'}</p>}
        </>}
        {fixture.rounds.length === 0 ? <p>El fixture todavía no está disponible.</p> : <>
            <label htmlFor="fixture-round">Ronda</label>{' '}
            <select id="fixture-round" value={selectedRound ?? ''}
                    onChange={event => setSelectedRound(Number(event.target.value))}>
                {fixture.rounds.map(round => <option key={round.number} value={round.number}>Ronda {round.number}</option>)}
            </select>
            {round && <>
                <MatchDate round={round}/>
                {round.byeClubId != null && <p>
                    Descansa: {clubs.find(club => club.id === round.byeClubId)?.name}.
                </p>}
                <ul className="league-fixture-matches">{round.matches.map(match => (
                    <li key={match.matchId} className={next?.matchId === match.matchId ? 'league-next-match' : ''}>
                        <strong>{match.creatorClubName} vs {match.visitorClubName}</strong>
                        <span>{states[match.status]}</span>
                        {['RUNNING', 'FINISHED'].includes(match.status) && <span>{match.localScore} - {match.visitorScore}</span>}
                        {clubId != null && [match.creatorClubId, match.visitorClubId].includes(clubId) && (
                            <Link
                                to={routePath(routes.match, {matchId: match.matchId})}
                                state={{leagueId: id}}
                                className={buttonVariants({size: 'sm', variant: 'outline'})}
                            >
                                Ver partido
                            </Link>
                        )}
                    </li>
                ))}</ul>
            </>}
        </>}
    </section>;
}
