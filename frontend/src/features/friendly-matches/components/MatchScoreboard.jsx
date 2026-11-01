import ClubAvatar from '@/features/my-club/components/ClubAvatar.jsx';

export function formatClock(milliseconds) {
    const seconds = Math.floor(milliseconds / 1000);
    return `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
}

function ScoreboardTeam({team, visitor = false}) {
    const name = team?.name || (visitor ? 'Esperando rival' : 'Local');

    return (
        <div
            className={`match-team${visitor ? ' match-team-visitor' : ''}`}
            style={{'--match-team-color': team?.color || (visitor ? '#f47280' : '#5fb4f5')}}
        >
            <div className="match-team-identity">
                <span className="match-team-label">{visitor ? 'Visitante' : 'Local'}</span>
                <h2>{name}</h2>
            </div>
            <div className="match-team-crest">
                {team ? (
                    <ClubAvatar avatar={team.avatar} clubName={name} size="md"/>
                ) : (
                    <span className="match-team-pending" aria-hidden="true">?</span>
                )}
            </div>
        </div>
    );
}

export default function MatchScoreboard({state}) {
    const [local, visitor] = state.teams;
    return (
        <section className="match-scoreboard" aria-label="Marcador del partido">
            <ScoreboardTeam team={local}/>
            <p className="match-score" aria-live="polite"
               aria-label={`Marcador: ${local?.score ?? 0} a ${visitor?.score ?? 0}`}>
                <span className="match-score-value">{local?.score ?? 0}</span>
                <span className="match-score-divider" aria-hidden="true">–</span>
                <span className="match-score-value">{visitor?.score ?? 0}</span>
            </p>
            <ScoreboardTeam team={visitor} visitor/>
            <div className="match-clock-panel">
                <span className="match-clock-label">Tiempo</span>
                <p className="match-clock" aria-label="Reloj del partido">
                    {formatClock(state.clockMs)}
                    <span className="match-clock-duration">/ {formatClock(state.durationMs)}</span>
                </p>
            </div>
        </section>
    );
}
