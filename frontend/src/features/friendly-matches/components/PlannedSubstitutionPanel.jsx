import {useEffect, useRef, useState} from 'react';
import {planSubstitution} from '../matchApi.js';
import {isPaused} from '../matchSnapshot.js';

const pauseNames = {1: 'primera hidratación', 2: 'entretiempo', 3: 'segunda hidratación'};

export default function PlannedSubstitutionPanel({matchId, state, sequence, clubId, connected}) {
    const [outId, setOutId] = useState('');
    const [inId, setInId] = useState('');
    const [receipt, setReceipt] = useState(null);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const attempt = useRef(null);
    const inFlight = useRef(false);
    const controller = useRef(null);
    useEffect(() => () => controller.current?.abort(), []);

    const team = state.lineups?.find(lineup => lineup.clubId === clubId);
    if (!team) return null;
    const next = state.nextPause;
    const pending = receipt?.sequence > sequence
        ? (receipt.status === 'PENDING' && receipt.pauseId === next?.pauseId ? receipt : null)
        : team.pendingSubstitution;
    const roster = [...team.starters, ...team.substitutes];
    const name = id => roster.find(player => player.playerId === id)?.name ?? `Jugador ${id}`;
    const lastEvent = (state.events ?? []).filter(event => event.clubId === clubId
        && ['SUBSTITUTION_APPLIED', 'SUBSTITUTION_REJECTED'].includes(event.type)).at(-1);
    const selectedOut = team.starters.some(p => String(p.playerId) === outId) ? outId
        : String(pending?.outPlayerId ?? '');
    const selectedIn = team.substitutes.some(p => String(p.playerId) === inId) ? inId
        : String(pending?.inPlayerId ?? '');
    const canPlan = connected && state.status === 'RUNNING' && !isPaused(state)
        && next && team.remainingSubstitutions > 0 && team.substitutes.length > 0;

    async function submit(event) {
        event.preventDefault();
        if (!canPlan || !selectedOut || !selectedIn || inFlight.current) return;
        const signature = `${selectedOut}:${selectedIn}`;
        if (attempt.current?.signature !== signature) {
            attempt.current = {signature, commandId: crypto.randomUUID()};
        }
        inFlight.current = true;
        setSaving(true);
        setError('');
        controller.current = new AbortController();
        try {
            const result = await planSubstitution(matchId, {
                outPlayerId: Number(selectedOut), inPlayerId: Number(selectedIn),
                commandId: attempt.current.commandId,
            }, controller.current.signal);
            setReceipt(result);
        } catch (cause) {
            if (cause.name !== 'AbortError') setError(cause.message);
        } finally {
            inFlight.current = false;
            setSaving(false);
        }
    }

    return (
        <section className="match-substitution" aria-label="Sustitución programada">
            <h2>Planificar sustitución</h2>
            {next && <p>Próxima pausa: {pauseNames[next.number]}.</p>}
            {pending && state.status === 'RUNNING' && (
                <p role="status">Cambio planificado: sale {name(pending.outPlayerId)} y entra {name(pending.inPlayerId)}.
                    {' '}Se aplicará en {pauseNames[next?.number]}; todavía no se realizó.</p>
            )}
            {lastEvent && (
                <p role="status">{lastEvent.type === 'SUBSTITUTION_APPLIED'
                    ? `Cambio aplicado: salió ${name(lastEvent.outPlayerId)} y entró ${name(lastEvent.inPlayerId)}.`
                    : 'El motor rechazó el cambio programado; no se aplicó.'}</p>
            )}
            {state.status === 'RUNNING' && (
                <>
                    {!next && <p>No quedan pausas para programar cambios.</p>}
                    {isPaused(state) && <p>La planificación se habilita al reanudar el juego.</p>}
                    {!connected && <p>Esperando conexión para planificar.</p>}
                    {team.remainingSubstitutions === 0 && next && <p>No hay cambios disponibles para esta pausa.</p>}
                    {team.substitutes.length === 0 && <p>Este partido no tiene suplentes guardados.</p>}
                    <form onSubmit={submit}>
                        <fieldset disabled={!canPlan || saving}>
                            <label>Titular que sale
                                <select value={selectedOut} onChange={event => setOutId(event.target.value)}>
                                    <option value="">Elegí un titular</option>
                                    {team.starters.map(player => <option key={player.playerId} value={player.playerId}>{player.name}</option>)}
                                </select>
                            </label>
                            <label>Suplente que entra
                                <select value={selectedIn} onChange={event => setInId(event.target.value)}>
                                    <option value="">Elegí un suplente</option>
                                    {team.substitutes.map(player => <option key={player.playerId} value={player.playerId}>{player.name}</option>)}
                                </select>
                            </label>
                            <button type="submit" disabled={!selectedOut || !selectedIn || saving}>
                                {saving ? 'Guardando…' : pending ? 'Reemplazar planificación' : 'Guardar cambio'}
                            </button>
                        </fieldset>
                    </form>
                </>
            )}
            {error && <p role="alert">{error}</p>}
        </section>
    );
}
