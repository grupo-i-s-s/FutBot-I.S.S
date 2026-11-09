import {useEffect, useRef, useState} from 'react';
import {planSubstitution, requestSubstitution} from '../matchApi.js';
import {isPaused} from '../matchSnapshot.js';
import {ArrowDownLeft, ArrowLeftRight, ArrowUpRight, CalendarClock} from 'lucide-react';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Card, CardContent, CardHeader} from '@/components/ui/card';

const SELECT_CLASSES = 'h-10 w-full min-w-0 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60';

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
        <p role="status" className="rounded-lg border border-primary/15 bg-secondary/50 px-4 py-3 text-sm text-primary">{lastEvent.type === 'SUBSTITUTION_APPLIED'
            ? lastEvent.source === 'DT'
                ? `El DT hizo un cambio. Salió ${name(lastEvent.outPlayerId)} y entró ${name(lastEvent.inPlayerId)}.`
                : `Cambio aplicado: salió ${name(lastEvent.outPlayerId)} y entró ${name(lastEvent.inPlayerId)}.`
            : 'El motor rechazó el cambio; no se aplicó.'}</p>
    );

    if (!allowManualActions) {
        return eventNotice ? (
            <Card className="my-6" role="region" aria-label="Sustituciones">
                <CardHeader><h2 className="flex items-center gap-2 text-lg font-bold"><ArrowLeftRight className="size-5" aria-hidden="true"/> Sustituciones</h2></CardHeader>
                <CardContent>{eventNotice}</CardContent>
            </Card>
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
        <Card className="my-6 rounded-2xl" role="region" aria-label={paused ? 'Sustitución durante la pausa' : 'Sustitución programada'}>
            <CardHeader className="gap-3 border-b px-5 pb-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
                            {paused ? <ArrowLeftRight className="size-5" aria-hidden="true"/> : <CalendarClock className="size-5" aria-hidden="true"/>}
                        </span>
                        <div className="space-y-1">
                            <h2 className="text-lg font-bold">{paused ? 'Sustitución en la pausa actual' : 'Planificar sustitución'}</h2>
                            {paused ? team.remainingSubstitutions > 0 && <p className="text-sm text-muted-foreground">El cambio se realizará en esta pausa: {pauseNames[state.breakIndex]}.</p>
                                : next && <p className="text-sm text-muted-foreground">Próxima pausa: {pauseNames[next.number]}.</p>}
                        </div>
                    </div>
                    {state.status === 'RUNNING' && <Badge variant="secondary">{team.remainingSubstitutions} {team.remainingSubstitutions === 1 ? 'cambio disponible' : 'cambios disponibles'}</Badge>}
                </div>
            </CardHeader>
            <CardContent className="space-y-4 px-5">
                {pending && state.status === 'RUNNING' && !paused && (
                    <p role="status" className="rounded-lg border border-primary/15 bg-secondary/50 px-4 py-3 text-sm text-primary">Cambio planificado: sale {name(pending.outPlayerId)} y entra {name(pending.inPlayerId)}.
                        {' '}Se aplicará en {pauseNames[next?.number]}; todavía no se realizó.</p>
                )}
                {waiting && <p role="status" className="rounded-lg bg-muted p-3 text-sm">Cambio pendiente: esperando la confirmación del motor.</p>}
                {eventNotice}
                {state.status === 'RUNNING' && (
                    <>
                        {!paused && !next && <p className="text-sm text-muted-foreground">No quedan pausas para programar cambios.</p>}
                        {!connected && <p className="text-sm text-muted-foreground">Esperando conexión para {paused ? 'realizar el cambio' : 'planificar'}.</p>}
                        {team.remainingSubstitutions === 0 && (paused || next) && <p className="text-sm text-muted-foreground">No hay cambios disponibles para esta pausa.</p>}
                        {team.substitutes.length === 0 && <p className="text-sm text-muted-foreground">Este partido no tiene suplentes guardados.</p>}
                        {(!paused || team.remainingSubstitutions > 0) && <form onSubmit={submit}>
                            <fieldset className="grid items-end gap-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" disabled={!(paused ? canChange : canPlan) || saving}>
                                <label className="grid min-w-0 gap-2 text-sm font-medium">
                                    <span className="flex items-center gap-1.5"><ArrowUpRight className="size-4 text-destructive" aria-hidden="true"/> Titular que sale</span>
                                    <select className={SELECT_CLASSES} value={selectedOut} onChange={event => setOutId(event.target.value)}>
                                        <option value="">Elegí un titular</option>
                                        {team.starters.map(player => <option key={player.playerId} value={player.playerId}>{player.name}</option>)}
                                    </select>
                                </label>
                                <label className="grid min-w-0 gap-2 text-sm font-medium">
                                    <span className="flex items-center gap-1.5"><ArrowDownLeft className="size-4 text-primary" aria-hidden="true"/> Suplente que entra</span>
                                    <select className={SELECT_CLASSES} value={selectedIn} onChange={event => setInId(event.target.value)}>
                                        <option value="">Elegí un suplente</option>
                                        {team.substitutes.map(player => <option key={player.playerId} value={player.playerId}>{player.name}</option>)}
                                    </select>
                                </label>
                                <Button type="submit" className="h-10 sm:col-span-2 lg:col-span-1" disabled={!selectedOut || !selectedIn || saving}>
                                    <ArrowLeftRight aria-hidden="true"/>{saving ? 'Guardando…' : paused ? 'Realizar cambio' : pending ? 'Reemplazar planificación' : 'Guardar cambio'}
                                </Button>
                            </fieldset>
                        </form>}
                    </>
                )}
                {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
            </CardContent>
        </Card>
    );
}
