import {useEffect, useRef, useState} from 'react';
import {Link, useParams} from 'react-router';

import {ArrowLeft, CircleAlert, ClipboardList, RefreshCw, Save, Users} from 'lucide-react';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardContent, CardDescription, CardHeader} from '@/components/ui/card';
import { getLeagueLineup, getLineupCatalogs, updateLeagueLineup} from './api';
import { changeSlot, toDraft, toPayload, validateDraft} from './lineupForm';
import {routePath, routes} from '@/routes.js';


const SELECT_CLASSES =
    'h-10 w-full min-w-0 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-60';


function LeagueLineupEditor({leagueId}) {
    const [saved, setSaved] = useState(null);
    const [draft, setDraft] = useState(null);
    const [catalogs, setCatalogs] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [conflict, setConflict] = useState(false);
    const [attempt, setAttempt] = useState(0);

    const saveController = useRef(null);

    useEffect(() => {
        const controller = new AbortController();
        const options = {signal: controller.signal};

        async function load() {
            setLoading(true);
            setError('');
            setSuccess('');

            try {
                const [response, available] = await Promise.all([
                    getLeagueLineup(leagueId, options),
                    getLineupCatalogs(options),
                ]);

                if (controller.signal.aborted) return;

                setSaved(response);
                setDraft(toDraft(response.lineUp));
                setCatalogs(available);
                setConflict(false);
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(
                        err.message || 'No se pudo cargar el plantel de la liga.',
                    );
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        load();

        return () => {
            controller.abort();
            saveController.current?.abort();
        };
    }, [leagueId, attempt]);

    function clearFeedback() {
        setError('');
        setSuccess('');
    }

    function handleSlotChange(index, field, value) {
        clearFeedback();

        setDraft((current) =>
            changeSlot(current, index, field, value, catalogs),
        );
    }

    async function handleSubmit(event) {
        event.preventDefault();

        if ( saveController.current || loading || !saved?.editable || conflict || !draft || validateDraft(draft, catalogs)) return;

        const controller = new AbortController();
        saveController.current = controller;

        setSaving(true);
        clearFeedback();

        try {
            const response = await updateLeagueLineup(
                leagueId,
                toPayload(draft, saved.version),
                {signal: controller.signal},
            );

            if (controller.signal.aborted) return;

            setSaved(response);
            setDraft(toDraft(response.lineUp));
            setConflict(false);
            setSuccess('Plantel guardado para el próximo partido de esta liga.');
        } catch (err) {
            if (controller.signal.aborted) return;

            if (err.code === 'LEAGUE_LINEUP_CONFLICT') {
                setConflict(true);
            }

            if (err.code === 'LEAGUE_CLOSED') {
                setSaved((current) => ({...current, editable: false}));
            }

            setError(
                Object.values(err.fields ?? {}).join(' ') ||
                err.message ||
                'No se pudo guardar el plantel.',
            );
        } finally {
            if (saveController.current === controller) {
                saveController.current = null;
            }

            if (!controller.signal.aborted) {
                setSaving(false);
            }
        }
    }

    if (!saved) {
        return (
            <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
                <Link to={routePath(routes.leagueLobby, {id: leagueId})} className={buttonVariants({variant: 'outline'})}>
                    <ArrowLeft aria-hidden="true"/> Volver a la liga
                </Link>
                <Card>
                    <CardHeader><h1 className="text-2xl font-bold">Plantel de liga</h1></CardHeader>
                    <CardContent className="space-y-4">
                        {loading && <p role="status" className="text-muted-foreground">Cargando plantel...</p>}
                        {error && <Alert variant="destructive"><CircleAlert aria-hidden="true"/><AlertDescription>{error}</AlertDescription></Alert>}
                        <Button type="button" variant="outline" disabled={loading} onClick={() => setAttempt(value => value + 1)}>
                            Reintentar
                        </Button>
                    </CardContent>
                </Card>
            </main>
        );
    }

    const busy = loading || saving;
    const locked = busy || !saved.editable;
    const validation = saved.editable ? validateDraft(draft, catalogs) : '';

    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
            <Link to={routePath(routes.leagueLobby, {id: leagueId})} className={buttonVariants({variant: 'outline'})}>
                <ArrowLeft aria-hidden="true"/> Volver a la liga
            </Link>
            <header className="flex items-center gap-4">
                <span className="flex size-16 shrink-0 items-center justify-center rounded-2xl bg-secondary text-primary">
                    <Users className="size-8" aria-hidden="true"/>
                </span>
                <div className="min-w-0 space-y-2">
                    <h1 className="text-2xl font-bold tracking-tight wrap-anywhere sm:text-3xl">Plantel de {saved.leagueName}</h1>
                    <Badge variant="secondary">{saved.editable ? 'Configuración del equipo' : 'Solo lectura'}</Badge>
                </div>
            </header>

            {!saved.editable && (
                <Alert role="status"><AlertDescription>La liga terminó o fue cancelada. El plantel es de solo lectura.</AlertDescription></Alert>
            )}
            {loading && <p role="status" className="text-sm text-muted-foreground">Recargando plantel...</p>}

            <form aria-label="Plantel de la liga" onSubmit={handleSubmit} className="space-y-6" noValidate aria-busy={busy}>
                <Card>
                    <CardHeader>
                        <h2 className="flex items-center gap-2 text-lg font-bold"><ClipboardList className="size-5" aria-hidden="true"/> Formación de la liga</h2>
                        <CardDescription>Se aplica desde el próximo partido. El partido en curso conserva su plantel.</CardDescription>
                    </CardHeader>
                    <CardContent className="grid items-start gap-4 sm:grid-cols-2">
                        <label className="block space-y-2 text-sm font-medium">
                            <span>Formación</span>
                            <select className={SELECT_CLASSES} value={draft.formationId} disabled={locked}
                                onChange={event => {
                                    clearFeedback();
                                    setDraft(current => ({...current, formationId: event.target.value}));
                                }}>
                                <option value="">Elegir formación</option>
                                {catalogs.formations.map(formation => <option key={formation.id} value={formation.id}>{formation.name}</option>)}
                            </select>
                        </label>
                        <p className="text-sm leading-relaxed text-muted-foreground">
                            El equipo de Mi club se configura por separado. Si elegís un jugador que ya ocupa otro puesto, se intercambian los lugares.
                        </p>
                    </CardContent>
                </Card>

                <div className="grid gap-6 lg:grid-cols-2">
                    {[{title: 'Titulares', start: 0}, {title: 'Suplentes', start: 3}].map(group => (
                        <section key={group.title} className="min-w-0 space-y-4" aria-label={group.title}>
                            <div className="flex items-center gap-2">
                                <h2 className="text-lg font-bold">{group.title}</h2>
                                <Badge variant="outline">3 jugadores</Badge>
                            </div>
                            {draft.slots.slice(group.start, group.start + 3).map((slot, slotIndex) => {
                                const index = group.start + slotIndex;
                                const title = index < 3 ? `Titular ${index + 1}` : `Suplente ${index - 2}`;
                                const missingSavedBehaviour = !saved.editable && slot.behaviourId
                                    && !catalogs.behaviours.some(({id}) => String(id) === slot.behaviourId);

                                return (
                                    <fieldset key={index} disabled={locked} className="min-w-0 space-y-4 rounded-xl border bg-card p-5 shadow-xs">
                                        <legend className="rounded-md border bg-secondary px-3 py-1 text-sm font-semibold text-primary">{title}</legend>
                                        <div className="grid gap-4 sm:grid-cols-2">
                                            <label className="block min-w-0 space-y-2 text-sm font-medium">
                                                <span>Jugador {title.toLowerCase()}</span>
                                                <select className={SELECT_CLASSES} value={slot.playerId}
                                                    onChange={event => handleSlotChange(index, 'playerId', event.target.value)}>
                                                    <option value="">Elegir jugador</option>
                                                    {catalogs.players.map(player => <option key={player.id} value={player.id}>{player.name}</option>)}
                                                </select>
                                            </label>
                                            <label className="block min-w-0 space-y-2 text-sm font-medium">
                                                <span>Comportamiento {title.toLowerCase()}</span>
                                                <select className={SELECT_CLASSES} value={slot.behaviourId}
                                                    onChange={event => handleSlotChange(index, 'behaviourId', event.target.value)}>
                                                    <option value="">Elegir comportamiento</option>
                                                    {missingSavedBehaviour && <option value={slot.behaviourId}>Comportamiento guardado #{slot.behaviourId}</option>}
                                                    {catalogs.behaviours.map(behaviour => <option key={behaviour.id} value={behaviour.id}>{behaviour.name}</option>)}
                                                </select>
                                            </label>
                                        </div>
                                    </fieldset>
                                );
                            })}
                        </section>
                    ))}
                </div>

                <Card>
                    <CardContent className="space-y-4">
                        {validation && <p className="text-sm text-muted-foreground">{validation}</p>}
                        {error && <Alert variant="destructive"><CircleAlert aria-hidden="true"/><AlertDescription>{error}</AlertDescription></Alert>}
                        {conflict && <p className="text-sm text-muted-foreground">Hubo otra edición. Tu borrador se conserva, pero necesitás recargar la versión guardada antes de volver a guardar.</p>}
                        {success && <Alert role="status" className="border-primary/20 bg-secondary/50"><AlertDescription className="text-primary">{success}</AlertDescription></Alert>}
                        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end">
                            <Button type="button" variant="outline" className="h-10" disabled={busy} onClick={() => setAttempt(value => value + 1)}>
                                <RefreshCw aria-hidden="true"/> Recargar plantel
                            </Button>
                            <Button type="submit" className="h-10" disabled={locked || conflict || Boolean(validation)}>
                                <Save aria-hidden="true"/>{saving ? 'Guardando...' : 'Guardar plantel'}
                            </Button>
                        </div>
                        <p className="text-sm text-muted-foreground sm:text-right">Recargar reemplaza tu borrador por el plantel guardado.</p>
                    </CardContent>
                </Card>
            </form>
        </main>
    );
}


export default function LeagueLineupPage() {
    const {id} = useParams();

    return <LeagueLineupEditor key={id} leagueId={id}/>;
}
