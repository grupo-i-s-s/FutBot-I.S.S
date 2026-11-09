import {useEffect, useRef, useState} from 'react';
import {planSubstitution, requestSubstitution} from '../matchApi.js';
import {isPaused} from '../matchSnapshot.js';

const pauseNames = {1: 'primera hidratación', 2: 'entretiempo', 3: 'segunda hidratación'};

export default function PlannedSubstitutionPanel({matchId, state, sequence, clubId, connected, allowManualActions}) {
    const [outId, setOutId] = useState('');
    const [inId, setInId] = useState('');
    const [receipt, setReceipt] = useState(null);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const attempt = useRef(null);
    const inFlight = useRef(false);
    const controller = useRef(null);
    const paused = isPaused(state);
    const next = state.nextPause;
    const pauseId = paused
        ? ([1, 2, 3].includes(state.breakIndex) ? `${matchId}:${state.breakIndex}` : null)
        : next?.pauseId;
    const context = `${state.status}:${paused ? 'manual' : 'planned'}:${pauseId}`;
    const currentContext = useRef(context);
    currentContext.current = context;
    useEffect(() => {
        controller.current?.abort();
        inFlight.current = false;
        setSaving(false);
        setError('');
    }, [context]);
    useEffect(() => () => controller.current?.abort(), []);

    const team = state.lineups?.find(lineup => lineup.clubId === clubId);
    if (!team) return null;
    const roster = [...team.starters, ...team.substitutes];
    const name = id => roster.find(player => player.playerId === id)?.name ?? `Jugador ${id}`;
    const lastEvent = (state.events ?? []).filter(event => event.clubId === clubId
        && ['SUBSTITUTION_APPLIED', 'SUBSTITUTION_REJECTED'].includes(event.type)).at(-1);
    const eventNotice = lastEvent && (
        <p role="status">{lastEvent.type === 'SUBSTITUTION_APPLIED'
            ? lastEvent.source === 'DT'
                ? `El DT hizo un cambio. Salió ${name(lastEvent.outPlayerId)} y entró ${name(lastEvent.inPlayerId)}.`
                : `Cambio aplicado: salió ${name(lastEvent.outPlayerId)} y entró ${name(lastEvent.inPlayerId)}.`
            : 'El motor rechazó el cambio; no se aplicó.'}</p>
    );

    if (!allowManualActions) {
        return eventNotice ? (
            <section className="match-substitution" aria-label="Sustituciones">
                <h2>Sustituciones</h2>
                {eventNotice}
            </section>
        ) : null;
    }

    const pending = !receipt?.manual && receipt?.sequence > sequence
        ? (receipt.status === 'PENDING' && receipt.pauseId === pauseId ? receipt : null)
        : team.pendingSubstitution;
    const accepted = paused && receipt?.manual && receipt.pauseId === pauseId && receipt.status === 'PENDING';
    const resolved = accepted && (team.remainingSubstitutions === 0
        || (lastEvent?.eventId !== receipt.previousEventId && lastEvent?.pauseId === pauseId && lastEvent.outPlayerId === receipt.outPlayerId
            && lastEvent.inPlayerId === receipt.inPlayerId));
    const waiting = accepted && !resolved;
    const selectedOut = team.starters.some(p => String(p.playerId) === outId) ? outId
        : String(pending?.outPlayerId ?? '');
    const selectedIn = team.substitutes.some(p => String(p.playerId) === inId) ? inId
        : String(pending?.inPlayerId ?? '');
    const canPlan = connected && state.status === 'RUNNING' && !paused
        && pauseId && team.remainingSubstitutions > 0 && team.substitutes.length > 0;
    const canChange = connected && paused && pauseId && team.remainingSubstitutions > 0
        && team.substitutes.length > 0 && !waiting;

    async function submit(event) {
        event.preventDefault();
        if (!(paused ? canChange : canPlan) || !selectedOut || !selectedIn || inFlight.current) return;
        const signature = `${context}:${selectedOut}:${selectedIn}`;
        if (attempt.current?.signature !== signature || resolved) {
            attempt.current = {signature, commandId: crypto.randomUUID()};
        }
        inFlight.current = true;
        setSaving(true);
        setError('');
        controller.current = new AbortController();
        try {
            const result = await (paused ? requestSubstitution : planSubstitution)(matchId, {
                outPlayerId: Number(selectedOut), inPlayerId: Number(selectedIn),
                commandId: attempt.current.commandId,
                pauseId,
            }, controller.current.signal);
            if (currentContext.current === context) {
                setReceipt({...result, manual: paused, previousEventId: lastEvent?.eventId});
                if (result.status === 'EXPIRED') setError('La pausa ya no está disponible. El cambio quedó sin efecto.');
            }
        } catch (cause) {
            if (currentContext.current === context && cause.name !== 'AbortError') setError(cause.message);
        } finally {
            if (currentContext.current === context) {
                inFlight.current = false;
                setSaving(false);
            }
        }
    }

    return (
        <section className="match-substitution" aria-label={paused ? 'Sustitución durante la pausa' : 'Sustitución programada'}>
            <h2>{paused ? 'Sustitución en la pausa actual' : 'Planificar sustitución'}</h2>
            {paused ? team.remainingSubstitutions > 0 && <p>El cambio se realizará en esta pausa: {pauseNames[state.breakIndex]}.</p>
                : next && <p>Próxima pausa: {pauseNames[next.number]}.</p>}
            {pending && state.status === 'RUNNING' && !paused && (
                <p role="status">Cambio planificado: sale {name(pending.outPlayerId)} y entra {name(pending.inPlayerId)}.
                    {' '}Se aplicará en {pauseNames[next?.number]}; todavía no se realizó.</p>
            )}
            {waiting && <p role="status">Cambio pendiente: esperando la confirmación del motor.</p>}
            {eventNotice}
            {state.status === 'RUNNING' && (
                <>
                    {!paused && !next && <p>No quedan pausas para programar cambios.</p>}
                    {!connected && <p>Esperando conexión para {paused ? 'realizar el cambio' : 'planificar'}.</p>}
                    {team.remainingSubstitutions === 0 && (paused || next) && <p>No hay cambios disponibles para esta pausa.</p>}
                    {team.substitutes.length === 0 && <p>Este partido no tiene suplentes guardados.</p>}
                    {(!paused || team.remainingSubstitutions > 0) && <form onSubmit={submit}>
                        <fieldset disabled={!(paused ? canChange : canPlan) || saving}>
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
                                {saving ? 'Guardando…' : paused ? 'Realizar cambio' : pending ? 'Reemplazar planificación' : 'Guardar cambio'}
                            </button>
                        </fieldset>
                    </form>}
                </>
            )}
            {error && <p role="alert">{error}</p>}
        </section>
    );
}
