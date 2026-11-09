import { Link, useParams } from 'react-router';
import { Button } from '@/components/ui/button';
import { useMatchConnection } from './hooks/useMatchConnection.js';
import MatchCanvas from './components/MatchCanvas.jsx';
import MatchScoreboard from './components/MatchScoreboard.jsx';
import './MatchPage.css';
import { isPaused } from './matchSnapshot.js';
import MatchBreakNotice, {
    breakLabel,
} from './components/MatchBreakNotice.jsx';
import LiveChangeBehaviour from './components/MatchBehaviourChanges.jsx';
import { useState, useEffect } from 'react'
import { request } from '@/api/http.js';

const connectionLabels = {
    loading: 'Cargando partido...', connecting: 'Conectando...', reconnecting: 'Reconectando...',
    disconnected: 'Sin conexión', error: 'No se pudo abrir el partido',
};

function resultText(state) {
    if (state.status === 'CANCELLED') return 'Partido cancelado.';
    const [local, visitor] = state.teams;
    if (local.score === visitor.score) return 'El partido terminó en empate.';
    return `Ganó ${local.score > visitor.score ? local.name : visitor.name}.`;
}

export default function MatchPage() {
    const { matchId } = useParams();
    const { snapshot, connectionStatus, error, retry } = useMatchConnection(matchId);
    const [myClubId, setMyClubId] = useState(null);
    const [behaviours, setBehaviours] = useState([])

    useEffect(() => {
        async function fetchMyClub() {
            const club = await request('/club/me');
            const player_behaviours = await request('/behaviours')
            console.log("Datps que devuelve", club);
            setMyClubId(club.id);
            setBehaviours(player_behaviours.items);
        }
        fetchMyClub();
    }, []);

    const state = snapshot?.state;
    const terminal = ['FINISHED', 'CANCELLED'].includes(state?.status);
    const connected = connectionStatus === 'connected';
    const paused = isPaused(state);

    const live = connected
        && state?.status === 'RUNNING'
        && !paused;

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

    return (
        <main className="match-page">
            <div className="match-page-content">
                <header className="match-page-header">
                    <div>
                        <p className="match-eyebrow">{isBehaviourTest ? '' : 'AMISTOSO'}</p>
                        <h1>{isBehaviourTest ? 'Prueba de comportamientos' : 'El partido'}</h1>
                    </div>
                    <Link to={isBehaviourTest ? '/behaviours' : '/partidos-disponibles'}>
                        {isBehaviourTest ? 'Volver a comportamientos' : 'Volver a amistosos'}
                    </Link>
                </header>
                <p className={`match-connection ${live ? 'match-connection-live' : ''}`} role="status">{label}</p>
                {error && <p className="match-error" role="alert">{error}</p>}
                {['error', 'disconnected'].includes(connectionStatus) && <Button onClick={retry}>Reintentar</Button>}
                {state && (
                    <>
                        <MatchScoreboard state={state} />
                        <MatchBreakNotice
                            state={state}
                            connected={connected}
                        />
                        {state.status === 'WAITING' &&
                            <p className="match-notice">Esperando el inicio del partido. Podés dejar esta página
                                abierta.</p>}
                        {terminal && <p className="match-result">{resultText(state)}</p>}
                        <MatchCanvas snapshot={snapshot} live={live} />
                        {state.players.length > 0 && (
                            <section className="match-lineups" aria-label="Jugadores en cancha">
                                {state.teams.map((team) => {
                                    const teamPlayers = state.players.filter((player) => player.teamId === team.id);

                                    const isMyTeam = myClubId ? team.id == myClubId : false;
                                    return (
                                        <div key={team.id}>
                                            <h2>
                                                <span style={{ backgroundColor: team.color }} />
                                                {team.name} {isMyTeam}
                                            </h2>
                                            <LiveChangeBehaviour
                                                match_id={matchId}
                                                players={teamPlayers}
                                                behaviours={behaviours}
                                                isMyTeam={isMyTeam}
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
