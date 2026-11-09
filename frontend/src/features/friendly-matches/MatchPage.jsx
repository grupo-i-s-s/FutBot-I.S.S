import { Link, useParams } from 'react-router';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { getMyClub, listBehaviours } from '../my-club/api.js';
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
import { activateMatchDt } from './matchApi.js';


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

function MatchDtControl({ matchId, team, running, connected }) {
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const active = team.dtActive === true;
    const configured = team.dtConfigured ?? active;
    const status = team.dtError ? 'DT con error' : active ? 'DT activo' : 'DT inactivo';

    async function toggle() {
        if (!running || !connected || !configured || saving) return;
        setSaving(true);
        setError('');
        try {
            await activateMatchDt(matchId, !active);
        } catch (cause) {
            setError(cause.message || 'No se pudo cambiar el estado del DT.');
        } finally {
            setSaving(false);
        }
    }

    if (!configured && !team.dtError) return null;

    return (
        <div className="text-sm">
            <div className="flex flex-wrap items-center gap-2">
                <span className={active && !team.dtError ? 'font-semibold text-emerald-800' : 'text-muted-foreground'}>
                    {status}
                </span>
                {running && configured && (
                    <Button type="button" variant="outline" size="sm" disabled={!connected || saving} onClick={toggle}>
                        {saving ? 'Guardando…' : active ? 'Desactivar DT' : 'Activar DT'}
                    </Button>
                )}
            </div>
            {team.dtError && <p className="match-error">{team.dtError}</p>}
            {error && <p className="match-error" role="alert">{error}</p>}
        </div>
    );
}

export default function MatchPage() {
    const { matchId } = useParams();
    const { snapshot, connectionStatus, error, retry } = useMatchConnection(matchId);
    const [myClubId, setMyClubId] = useState(null);
    const [behaviours, setBehaviours] = useState([]);
    const [controlsError, setControlsError] = useState('');

    useEffect(() => {
        const controller = new AbortController();
        const options = { signal: controller.signal };

        async function loadControls() {
            const [club, catalog] = await Promise.allSettled([
                getMyClub(options),
                listBehaviours(options),
            ]);
            if (controller.signal.aborted) return;
            if (club.status === 'fulfilled') setMyClubId(club.value.id);
            if (catalog.status === 'fulfilled') setBehaviours(catalog.value.items);
            if (club.status === 'rejected' || catalog.status === 'rejected') {
                setControlsError('No se pudieron cargar todos los controles de tu equipo.');
            }
        }

        loadControls();
        return () => controller.abort();
    }, []);

    const state = snapshot?.state;
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
                        {controlsError && <p className="match-error" role="alert">{controlsError}</p>}
                        <PlannedSubstitutionPanel key={matchId} matchId={matchId} state={state}
                                                  sequence={snapshot.sequence} clubId={myClubId} connected={connected}/>
                        {state.players.length > 0 && (
                            <section className="match-lineups" aria-label="Jugadores en cancha">
                                {state.teams.map((team) => {
                                    const teamPlayers = state.players.filter((player) => player.teamId === team.id);

                                    const isMyTeam = team.id === myClubId;
                                    return (
                                        <div key={team.id}>
                                            <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                                                <h2>
                                                    <span style={{ backgroundColor: team.color }} />
                                                    {team.name}
                                                </h2>
                                                {isMyTeam && (
                                                    <MatchDtControl key={matchId} matchId={matchId} team={team}
                                                                    running={running} connected={connected} />
                                                )}
                                            </div>
                                            <LiveChangeBehaviour
                                                key={matchId}
                                                matchId={matchId}
                                                players={teamPlayers}
                                                behaviours={behaviours}
                                                isMyTeam={isMyTeam}
                                                canEdit={running && connected}
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
