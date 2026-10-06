export function formatClock(milliseconds) {
    const seconds = Math.floor(milliseconds / 1000);
    return `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
}

export default function MatchScoreboard({state}) {
    const local = state.teams.find((team) => team.side === 'LEFT');
    const visitor = state.teams.find((team) => team.side === 'RIGHT');
    return (
        <section className="match-scoreboard" aria-label="Marcador del partido">
            <div className="match-team">
                <span className="match-team-label">Local</span>
                <h2>{local?.name ?? 'Local'}</h2>
            </div>
            <div className="match-score-center">
                <p className="match-score" aria-live="polite"
                   aria-label={`Marcador: ${local?.score ?? 0} a ${visitor?.score ?? 0}`}>
                    {local?.score ?? 0} <span aria-hidden="true">–</span> {visitor?.score ?? 0}
                </p>
                <p className="match-clock" aria-label="Reloj del partido">
                    {formatClock(state.clockMs)} <span>/ {formatClock(state.durationMs)}</span>
                </p>
            </div>
            <div className="match-team match-team-visitor">
                <span className="match-team-label">Visitante</span>
                <h2>{visitor?.name ?? 'Esperando rival'}</h2>
            </div>
        </section>
    );
}
