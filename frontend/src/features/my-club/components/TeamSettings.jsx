import { useEffect, useState } from 'react';
import { getDefaultTeam, getFormations, updateDefaultTeam, listPlayers, getPlayersByIds } from '../api';
import { Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, } from '@/components/ui/card';


const SELECT_CLASSES =
    'w-full min-w-0 rounded-md border border-input bg-background px-2 py-2 text-sm';

function loadTeam(response) {
    const { lineUp } = response;

    return {
        formation: String(lineUp.formationId),
        slots: [...lineUp.starters, ...lineUp.substitutes].map(
            (slot) => ({
                playerId: String(slot.playerId),
                behaviourId: String(slot.behaviourId),
            })
        ),
    };
}

<<<<<<< HEAD
export default function TeamSettings({ clubId, behaviours }) {
=======
export default function TeamSettings({
    clubId, players, behaviours, disabled = false, onSavingChange,
}) {
>>>>>>> origin/develop
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [team, setTeam] = useState(null);
    const [formations, setFormations] = useState([]);
    const [selectedPlayers, setSelectedPlayers] = useState([]);
    const [slotSearch, setSlotSearch] = useState({});
    const [slotResults, setSlotResults] = useState({});
    const [slotSearchErrors, setSlotSearchErrors] = useState({});
    const [activeGroup, setActiveGroup] = useState('starters');
    const [loading, setLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    function clearFeedback() {
        setError('');
        setSuccess('');
    }

    useEffect(() => {
        const controller = new AbortController();
        const options = { signal: controller.signal };

        async function fetchTeam() {
            setLoading(true);
            setError('');

            try {
                const [response, catalog] = await Promise.all([
                    getDefaultTeam(options),
                    getFormations(options),
                ]);

                if (controller.signal.aborted) return;

                if (!response) {
                    throw new Error('No se encontró el equipo guardado del club.');
                }

                const loadedTeam = loadTeam(response);
                const playerIds = loadedTeam.slots.map((slot) => Number(slot.playerId));
                const savedPlayers = await getPlayersByIds(playerIds, options);

                if (controller.signal.aborted) return;

                setTeam(loadedTeam);
                setSelectedPlayers(savedPlayers);
                setFormations(catalog.items);
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(err.message || 'No se pudo cargar el equipo.');
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        fetchTeam();
        return () => controller.abort();
    }, [clubId]);

    useEffect(() => {
        const controllers = [];
        const timeoutIds = [];

        Object.entries(slotSearch).forEach(([slotIndex, text]) => {
            const search = text.trim();
            if (!search) return;

            const controller = new AbortController();
            controllers.push(controller);

            const timeoutId = setTimeout(async () => {
                setSlotSearchErrors((current) => ({
                    ...current,
                    [slotIndex]: '',
                }));

                try {
                    const response = await listPlayers({
                        search,
                        page: 1,
                        limit: 10,
                        signal: controller.signal,
                    });

                    if (!controller.signal.aborted) {
                        setSlotResults((current) => ({
                            ...current,
                            [slotIndex]: response.items,
                        }));
                    }
                } catch (err) {
                    if (!controller.signal.aborted && err.name !== 'AbortError') {
                        setSlotSearchErrors((current) => ({
                            ...current,
                            [slotIndex]: err.message || 'No se pudieron buscar jugadores.',
                        }));
                    }
                }
            }, 250);

            timeoutIds.push(timeoutId);
        });

        return () => {
            timeoutIds.forEach(clearTimeout);
            controllers.forEach((controller) => controller.abort());
        };
    }, [slotSearch]);

    function changeSlot(index, field, value) {
        clearFeedback();

        setTeam((current) => ({
            ...current,
            slots: current.slots.map((slot, slotIndex) =>
                slotIndex === index
                    ? { ...slot, [field]: value }
                    : slot
            ),
        }));
    }

    function selectPlayer(slotIndex, player) {
        clearFeedback();

        setTeam((current) => ({
            ...current,
            slots: current.slots.map((slot, index) =>
                index === slotIndex
                    ? {
                        playerId: String(player.id),
                        behaviourId: String(player.behaviorId),
                    }
                    : slot
            ),
        }));

        setSelectedPlayers((current) => [
            ...current.filter((item) => item.id !== player.id),
            player,
        ]);

        setSlotSearch((current) => ({
            ...current,
            [slotIndex]: '',
        }));

        setSlotResults((current) => ({
            ...current,
            [slotIndex]: [],
        }));
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (disabled || isSaving || !team) return;
        clearFeedback();

        const playerIds = team.slots.map((slot) => slot.playerId);

        if (playerIds.some((id) => !id)) {
            setError('Elegí los 6 jugadores del equipo.');
            return;
        }

        if (new Set(playerIds).size !== 6) {
            setError('Un jugador no puede ocupar dos lugares.');
            return;
        }

        if (team.slots.some((slot) =>
            !behaviours.some(
                (behaviour) => String(behaviour.id) === slot.behaviourId
            )
        )) {
            setError('Elegí un comportamiento para cada jugador.');
            return;
        }

        if (!formations.some(
            (formation) => String(formation.id) === team.formation
        )) {
            setError('Elegí una formación disponible.');
            return;
        }

        const selections = team.slots.map((slot) => ({
            playerId: Number(slot.playerId),
            behaviourId: Number(slot.behaviourId),
        }));

        setIsSaving(true);
        onSavingChange?.(true);

        try {
            const response = await updateDefaultTeam({
                formationId: Number(team.formation),
                starters: selections.slice(0, 3),
                substitutes: selections.slice(3, 6),
            });

            setTeam(loadTeam(response));
            setSuccess('Equipo guardado correctamente.');
        } catch (err) {
            const fields = Object.values(err.fields ?? {}).join(' ');
            setError(
                fields || err.message || 'No se pudo guardar el equipo.'
            );
        } finally {
            setIsSaving(false);
            onSavingChange?.(false);
        }
    }

    if (loading) {
        return <p role="status">Cargando equipo...</p>;
    }
    if (!team) {
        return <p role="alert">{error}</p>;
    }

    const firstSlot = activeGroup === 'starters' ? 0 : 3;
    const visibleSlots = team.slots
        .map((slot, index) => ({ slot, index }))
        .slice(firstSlot, firstSlot + 3);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                    <Users className="size-5" aria-hidden="true" />
                    Mi equipo
                </CardTitle>
                <CardDescription>
                    Elegí la formación, los 3 titulares y los 3 suplentes
                    para tus próximos partidos.
                </CardDescription>
            </CardHeader>

            <CardContent>
                <form aria-label="Equipo para próximos partidos" onSubmit={handleSubmit} noValidate className="space-y-4">
                    <div className="space-y-1">
                        <label htmlFor="team-formation" className="text-sm font-medium">
                            Formación
                        </label>

                        <select
                            id="team-formation"
                            disabled={disabled || isSaving}
                            className={SELECT_CLASSES}
                            value={team.formation}
                            onChange={(event) => {
                                clearFeedback();
                                setTeam((current) => ({
                                    ...current,
                                    formation: event.target.value,
                                }));
                            }}
                        >
                            {formations.map((formation) => (
                                <option key={formation.id} value={formation.id}>
                                    {formation.name}
                                </option>
                            ))}
                        </select>

                        <p className="text-sm text-muted-foreground">
                            {selectedFormation?.description}
                        </p>
                        <p className="text-sm text-muted-foreground">
                            Se aplica a los próximos partidos. Los partidos ya
                            iniciados conservan su formación.
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <Button
                            type="button"
                            variant={activeGroup === 'starters' ? 'default' : 'outline'}
                            onClick={() => setActiveGroup('starters')}
                            aria-pressed={activeGroup === 'starters'}
                        >
                            Titulares
                        </Button>

                        <Button
                            type="button"
                            variant={activeGroup === 'substitutes' ? 'default' : 'outline'}
                            onClick={() => setActiveGroup('substitutes')}
                            aria-pressed={activeGroup === 'substitutes'}
                        >
                            Suplentes
                        </Button>
                    </div>
                    {visibleSlots.map(({ slot, index }) => (
                        <fieldset
                            key={index}
                            disabled={disabled || isSaving}
                            className="min-w-0 space-y-2 rounded-md border p-2"
                        >
                            <legend className="px-1 text-sm font-semibold">
                                {index < 3
                                    ? `Titular ${index + 1}${selectedFormation?.slots?.[index]?.label
                                        ? ` — ${selectedFormation.slots[index].label}` : ''}`
                                    : `Suplente ${index - 2}`}
                            </legend>

                            <div>
                                <label htmlFor={`team-player-${index}`} className="sr-only">
                                    Jugador del lugar {index + 1}
                                </label>

                                <div className="space-y-2">
                                    <p className="text-sm">
                                        Seleccionado:{' '}
                                        <strong>
                                            {selectedPlayers.find(
                                                (player) => String(player.id) === slot.playerId
                                            )?.name ?? 'Ninguno'}
                                        </strong>
                                    </p>

                                    <label htmlFor={`team-player-search-${index}`} className="sr-only">
                                        Buscar jugador para el lugar {index + 1}
                                    </label>

                                    <input
                                        id={`team-player-search-${index}`}
                                        type="search"
                                        className={SELECT_CLASSES}
                                        value={slotSearch[index] ?? ''}
                                        onChange={(event) => {
                                            const value = event.target.value;

                                            setSlotSearch((current) => ({
                                                ...current,
                                                [index]: value,
                                            }));

                                            if (!value.trim()) {
                                                setSlotResults((current) => ({
                                                    ...current,
                                                    [index]: [],
                                                }));
                                            }
                                        }}
                                        placeholder="Buscar jugador por nombre"
                                    />

                                    {slotSearchErrors[index] && (
                                        <p role="alert" className="text-sm text-destructive">
                                            {slotSearchErrors[index]}
                                        </p>
                                    )}

                                    <ul className="space-y-1">
                                        {(slotResults[index] ?? [])
                                            .filter((player) =>
                                                !team.slots.some(
                                                    (other, otherIndex) =>
                                                        otherIndex !== index &&
                                                        other.playerId === String(player.id)
                                                )
                                            )
                                            .map((player) => (
                                                <li key={player.id}>
                                                    <button
                                                        type="button"
                                                        className="w-full rounded-md border px-3 py-2 text-left text-sm hover:bg-muted"
                                                        onClick={() => selectPlayer(index, player)}
                                                    >
                                                        {player.name}
                                                    </button>
                                                </li>
                                            ))}
                                    </ul>
                                </div>
                            </div>

                            <div>
                                <label htmlFor={`team-behaviour-${index}`} className="sr-only">
                                    Comportamiento del lugar {index + 1}
                                </label>

                                <select
                                    id={`team-behaviour-${index}`}
                                    className={SELECT_CLASSES}
                                    value={slot.behaviourId}
                                    onChange={(event) =>
                                        changeSlot(index, 'behaviourId', event.target.value)
                                    }
                                >
                                    <option value="">Elegir comportamiento</option>

                                    {behaviours.map((behaviour) => (
                                        <option key={behaviour.id} value={behaviour.id}>
                                            {behaviour.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </fieldset>
                    ))}

                    {behaviours.length === 0 && (
                        <p className="text-sm text-destructive">
                            Necesitás comportamientos disponibles.
                        </p>
                    )}

                    <Button
                        type="submit"
                        className="w-full"
<<<<<<< HEAD
                        disabled={isSaving || behaviours.length === 0 || formations.length === 0}
=======
                        disabled={disabled || isSaving || players.length < 6 || behaviours.length === 0 || formations.length === 0}
>>>>>>> origin/develop
                    >
                        {isSaving ? 'Guardando...' : 'Guardar equipo'}
                    </Button>

                    {error && (
                        <p role="alert" className="text-sm text-destructive">
                            {error}
                        </p>
                    )}

                    {success && (
                        <p role="status" className="text-sm">
                            {success}
                        </p>
                    )}
                </form>
            </CardContent>
        </Card>
    );
}
