import {useEffect, useRef, useState} from 'react';
import {Link, useParams} from 'react-router';

import {Button} from '@/components/ui/button';
import { getLeagueLineup, getLineupCatalogs, updateLeagueLineup} from './api';
import { changeSlot, toDraft, toPayload, validateDraft} from './lineupForm';


const SELECT_CLASSES =
    'w-full rounded-md border border-input bg-background px-3 py-2';


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
            <main className="mx-auto max-w-3xl space-y-4 p-4">
                <h1 className="text-2xl font-bold">Plantel de liga</h1>

                {loading && <p role="status">Cargando plantel...</p>}
                {error && <p role="alert">{error}</p>}

                <Button
                    type="button"
                    disabled={loading}
                    onClick={() => setAttempt((value) => value + 1)}
                >
                    Reintentar
                </Button>
            </main>
        );
    }

    const busy = loading || saving;
    const locked = busy || !saved.editable;
    const validation = validateDraft(draft, catalogs);

    return (
        <main className="mx-auto max-w-3xl space-y-4 p-4">
            <Link
                to={`/leagues/${leagueId}/lobby`}
                className="underline"
            >
                Volver a la liga
            </Link>

            <h1 className="text-2xl font-bold">
                Plantel de {saved.leagueName}
            </h1>

            <p>
                Esta configuración pertenece a esta liga y se aplica desde
                el próximo partido.<br/> El partido en curso conserva su plantel.
            </p>

            <p className="text-sm text-muted-foreground">
                El equipo de Mi club se configura por separado. 
                Si elegís un jugador que ya ocupa otro puesto,
                se intercambian los lugares.
            </p>

            {!saved.editable && (
                <p role="status">
                    La liga terminó o fue cancelada. El plantel es de solo lectura.
                </p>
            )}

            {loading && <p role="status">Recargando plantel...</p>}

            <form
                aria-label="Plantel de la liga"
                onSubmit={handleSubmit}
                className="space-y-4"
                noValidate
            >
                <label className="block space-y-1">
                    <span>Formación</span>

                    <select
                        className={SELECT_CLASSES}
                        value={draft.formationId}
                        disabled={locked}
                        onChange={(event) => {
                            clearFeedback();
                            setDraft((current) => ({
                                ...current,
                                formationId: event.target.value,
                            }));
                        }}
                    >
                        <option value="">Elegir formación</option>

                        {catalogs.formations.map((formation) => (
                            <option key={formation.id} value={formation.id}>
                                {formation.name}
                            </option>
                        ))}
                    </select>
                </label>

                {draft.slots.map((slot, index) => {
                    const title = index < 3
                        ? `Titular ${index + 1}`
                        : `Suplente ${index - 2}`;

                    return (
                        <fieldset
                            key={index}
                            disabled={locked}
                            className="space-y-3 rounded-md border p-3"
                        >
                            <legend className="px-1 font-semibold">
                                {title}
                            </legend>

                            <label className="block space-y-1">
                                <span>Jugador {title.toLowerCase()}</span>

                                <select
                                    className={SELECT_CLASSES}
                                    value={slot.playerId}
                                    onChange={(event) =>
                                        handleSlotChange(
                                            index,
                                            'playerId',
                                            event.target.value,
                                        )
                                    }
                                >
                                    <option value="">Elegir jugador</option>

                                    {catalogs.players.map((player) => (
                                        <option key={player.id} value={player.id}>
                                            {player.name}
                                        </option>
                                    ))}
                                </select>
                            </label>

                            <label className="block space-y-1">
                                <span>Comportamiento {title.toLowerCase()}</span>

                                <select
                                    className={SELECT_CLASSES}
                                    value={slot.behaviourId}
                                    onChange={(event) =>
                                        handleSlotChange(
                                            index,
                                            'behaviourId',
                                            event.target.value,
                                        )
                                    }
                                >
                                    <option value="">Elegir comportamiento</option>

                                    {catalogs.behaviours.map((behaviour) => (
                                        <option
                                            key={behaviour.id}
                                            value={behaviour.id}
                                        >
                                            {behaviour.name}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        </fieldset>
                    );
                })}

                {validation && saved.editable && <p>{validation}</p>}

                {error && (
                    <p role="alert" className="text-destructive">
                        {error}
                    </p>
                )}

                {conflict && (
                    <p>
                        Hubo otra edición. Tu borrador se conserva,
                        pero necesitás recargar la versión guardada
                        antes de volver a guardar.
                    </p>
                )}

                <div className="flex flex-wrap gap-2">
                    <Button
                        type="submit"
                        disabled={locked || conflict || Boolean(validation)}
                    >
                        {saving ? 'Guardando...' : 'Guardar plantel'}
                    </Button>

                    <Button
                        type="button"
                        variant="outline"
                        disabled={busy}
                        onClick={() => setAttempt((value) => value + 1)}
                    >
                        Recargar plantel
                    </Button>
                </div>

                <p className="text-sm text-muted-foreground">
                    Recargar reemplaza tu borrador por el plantel guardado.
                </p>

                {success && <p role="status">{success}</p>}
            </form>
        </main>
    );
}


export default function LeagueLineupPage() {
    const {id} = useParams();

    return <LeagueLineupEditor key={id} leagueId={id}/>;
}