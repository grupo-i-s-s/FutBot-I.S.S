import {Link, useParams} from 'react-router';
import {Button} from '@/components/ui/button';
import {useMatchConnection} from './hooks/useMatchConnection.js';
import MatchCanvas from './components/MatchCanvas.jsx';
import MatchScoreboard from './components/MatchScoreboard.jsx';
import './MatchPage.css';

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
    const {matchId} = useParams();
    const {snapshot, connectionStatus, error, retry} = useMatchConnection(matchId);
    const state = snapshot?.state;
    const terminal = ['FINISHED', 'CANCELLED'].includes(state?.status);
    const live = connectionStatus === 'connected' && state?.status === 'RUNNING';
    const label = terminal ? (state.status === 'FINISHED' ? 'Finalizado' : 'Cancelado')
        : connectionLabels[connectionStatus] ?? (state?.status === 'WAITING' ? 'Esperando inicio' : 'En vivo');

    return (
        <main className="match-page">
            <div className="match-page-content">
                <header className="match-page-header">
                    <div><p className="match-eyebrow">AMISTOSO · {matchId}</p><h1>El partido</h1></div>
                    <Link to="/partidos-disponibles">Volver a amistosos</Link>
                </header>
                <p className={`match-connection ${live ? 'match-connection-live' : ''}`} role="status">{label}</p>
                {error && <p className="match-error" role="alert">{error}</p>}
                {['error', 'disconnected'].includes(connectionStatus) && <Button onClick={retry}>Reintentar</Button>}
                {state && (
                    <>
                        <MatchScoreboard state={state}/>
                        {state.status === 'WAITING' &&
                            <p className="match-notice">Esperando el inicio del partido. Podés dejar esta página
                                abierta.</p>}
                        {terminal && <p className="match-result">{resultText(state)}</p>}
                        <MatchCanvas snapshot={snapshot} live={live}/>
                        {state.players.length > 0 && (
                            <section className="match-lineups" aria-label="Jugadores en cancha">
                                {state.teams.map((team) => (
                                    <div key={team.id}>
                                        <h2><span style={{backgroundColor: team.color}}/>{team.name}</h2>
                                        <ul>{state.players.filter((player) => player.teamId === team.id).map((player) => (
                                            <li key={player.id}><span>#{player.id}</span> {player.name}</li>
                                        ))}</ul>
                                    </div>
                                ))}
                            </section>
                        )}
                    </>
                )}
            </div>
        </main>
    );
}
