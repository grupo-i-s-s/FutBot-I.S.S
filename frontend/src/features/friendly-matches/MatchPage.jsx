import { Link, useLocation, useParams } from 'react-router';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { listBehaviours } from '../behaviours/api.js';
import { useSession } from '../session/SessionProvider.jsx';
import { useMatchConnection } from './hooks/useMatchConnection.js';
import MatchCanvas from './components/MatchCanvas.jsx';
import MatchScoreboard from './components/MatchScoreboard.jsx';
import './MatchPage.css';
import { isPaused } from './matchSnapshot.js';
import MatchBreakNotice, {
    breakLabel,
} from './components/MatchBreakNotice.jsx';
import LiveChangeBehaviour from './components/MatchBehaviourChanges.jsx';
import PlannedSubstitutionPanel from './components/PlannedSubstitutionPanel.jsx';
import {routePath, routes} from '@/routes.js';

const connectionLabels = {
    loading: 'Cargando partido...', connecting: 'Conectando...', reconnecting: 'Reconectando...',
    disconnected: 'Sin conexión', error: 'No se pudo abrir el partido',
};

function resultText(state) {
    if (state.status === 'CANCELLED') {
        if (state.cancellationReason === 'LEAGUE_SCHEDULE_CONFLICT') {
            return 'El amistoso se canceló porque su horario se superpone con una ronda de liga confirmada.';
        }
        if (state.cancellationReason === 'CLUB_BUSY') {
            return 'El partido se canceló porque uno de los clubes ya estaba jugando otro partido.';
        }
        if (state.cancellationReason === 'CHECKPOINT_UNRECOVERABLE') {
            return 'El partido se canceló porque no se pudo recuperar el estado guardado. El marcador es parcial y el partido quedó sin resultado.';
        }
        return 'Partido cancelado.';
    }
    const [local, visitor] = state.teams;
    if (local.score === visitor.score) return 'El partido terminó en empate.';
    return `Ganó ${local.score > visitor.score ? local.name : visitor.name}.`;
}

function MatchDtStatus({ team }) {
    const active = team?.dtActive === true;
    if (!active && (team?.dtActive !== false || !team.dtConfigured)) return null;
    const dtError = active && team.dtError;
    const status = dtError ? 'DT con error' : active ? 'DT activo' : 'DT inactivo';

    return (
        <div className="match-notice">
            <p className="font-semibold">{status}</p>
            {active && <p>Estás viendo el partido en modo espectador.</p>}
            {dtError && <p className="match-error" role="alert">{dtError}</p>}
        </div>
    );
}

export default function MatchPage() {
    const { matchId } = useParams();
    const location = useLocation();
    const { snapshot, connectionStatus, error, retry } = useMatchConnection(matchId);
    const { club } = useSession();
    const [behaviours, setBehaviours] = useState([]);
    const [behavioursError, setBehavioursError] = useState('');

    useEffect(() => {
        const controller = new AbortController();
        listBehaviours({ signal: controller.signal }).then(({ items }) => {
            if (!controller.signal.aborted) setBehaviours(items);
        }).catch((requestError) => {
            if (!controller.signal.aborted) setBehavioursError(requestError.message);
        });
        return () => controller.abort();
    }, []);

    const state = snapshot?.state;
    const myTeam = state?.teams.find(team => team.id === club?.id);
    const allowManualActions = myTeam?.dtActive === false;
    const terminal = ['FINISHED', 'CANCELLED'].includes(state?.status);
    const connected = connectionStatus === 'connected';
    const paused = isPaused(state);
    const running = state?.status === 'RUNNING';

    const live = connected && running && !paused;

    const label = terminal
        ? (state.status === 'FINISHED' ? 'Finalizado' : 'Cancelado')
        : connectionLabels[connectionStatus]
        ?? (
            paused
                ? breakLabel(state)
                : state?.status === 'WAITING'
                    ? 'Esperando inicio'
                    : 'En vivo'
        );

    const isBehaviourTest = state?.teams?.some((team) => team.id === 999);
    const leagueId = Number(location.state?.leagueId);
    const leagueLobby = !isBehaviourTest && Number.isSafeInteger(leagueId) && leagueId > 0
        ? routePath(routes.leagueLobby, {id: leagueId}) : null;

    return (
        <main className="match-page">
            <div className="match-page-content">
                <header className="match-page-header">
                    <div>
                        <p className="match-eyebrow">{isBehaviourTest ? '' : leagueLobby ? 'LIGA' : 'AMISTOSO'}</p>
                        <h1>{isBehaviourTest ? 'Prueba de comportamientos' : 'El partido'}</h1>
                    </div>
                    <Link to={isBehaviourTest ? routes.behaviours : leagueLobby ?? location.state?.returnTo ?? routes.friendlyMatches}>
                        {isBehaviourTest ? 'Volver a comportamientos' : leagueLobby ? 'Volver a la liga' : 'Volver a amistosos'}
                    </Link>
                </header>
                <p className={`match-connection ${live ? 'match-connection-live' : ''}`} role="status">{label}</p>
                {error && <p className="match-error" role="alert">{error}</p>}
                {['error', 'disconnected'].includes(connectionStatus) && <Button onClick={retry}>Reintentar</Button>}
                {state && (
                    <>
                        <MatchScoreboard state={state} />
                        <MatchDtStatus team={myTeam} />
                        <MatchBreakNotice
                            state={state}
                            connected={connected}
                        />
                        {state.status === 'WAITING' &&
                            <p className="match-notice">Esperando el inicio del partido. Podés dejar esta página
                                abierta.</p>}
                        {terminal && <p className="match-result">{resultText(state)}</p>}
                        <MatchCanvas snapshot={snapshot} live={live} />
                        <PlannedSubstitutionPanel key={matchId} matchId={matchId} state={state}
                                                  sequence={snapshot.sequence} clubId={club?.id} connected={connected}
                                                  allowManualActions={allowManualActions}/>
                        {state.players.length > 0 && (
                            <section className="match-lineups" aria-label="Jugadores en cancha">
                                {state.teams.map((team) => {
                                    const teamPlayers = state.players.filter((player) => player.teamId === team.id);

                                    const isMyTeam = team.id === club?.id;
                                    return (
                                        <div key={team.id}>
                                            <h2>
                                                <span style={{ backgroundColor: team.color }} />
                                                {team.name}
                                            </h2>
                                            {isMyTeam && allowManualActions && running && behavioursError && (
                                                <p role="alert">No se pudieron cargar los comportamientos. {behavioursError}</p>
                                            )}
                                            <LiveChangeBehaviour
                                                key={matchId}
                                                matchId={matchId}
                                                players={teamPlayers}
                                                behaviours={behaviours}
                                                isMyTeam={isMyTeam}
                                                allowManualActions={allowManualActions}
                                                canChange={running && connected}
                                            />
                                        </div>
                                    );
                                })}
                            </section>
                        )}
                    </>
                )}
            </div>
        </main>
    );
}
