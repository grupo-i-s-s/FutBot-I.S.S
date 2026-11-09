import { useEffect, useId, useState } from 'react';
import { getDefaultTeam, getFormations, updateDefaultTeam, getPlayersByIds } from '../api';
import { Info, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, } from '@/components/ui/card';
import { Combobox, ComboboxContent, ComboboxEmpty, ComboboxInput, ComboboxItem, ComboboxList } from '@/components/ui/combobox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import TeamPlayerCombobox from './TeamPlayerCombobox';


const SELECT_CLASSES =
    'w-full min-w-0 rounded-md border border-input bg-background px-2 py-2 text-sm';
const LINEUP_GROUPS = [
    {name: 'Titulares', firstSlot: 0},
    {name: 'Suplentes', firstSlot: 3},
];

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

function TeamBehaviourCombobox({id, behaviour, behaviours, disabled, onSelect}) {
    const [query, setQuery] = useState(null);

    return (
        <Combobox
            items={behaviours}
            value={behaviour}
            inputValue={query ?? behaviour?.name ?? ''}
            disabled={disabled}
            itemToStringLabel={(item) => item.name}
            autoHighlight
            onInputValueChange={(text, {reason}) => {
                if (reason === 'input-change') setQuery(text);
            }}
            onOpenChange={(open) => {
                if (!open) setQuery(null);
            }}
            onValueChange={(item, details) => {
                if (!item) {
                    details.cancel();
                    return;
                }
                onSelect(item);
                setQuery(null);
            }}
        >
            <ComboboxInput
                id={id}
                placeholder="Buscar comportamiento"
                onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.nativeEvent.isComposing) event.preventDefault();
                }}
            />
            <ComboboxContent>
                <ComboboxEmpty>No se encontraron comportamientos.</ComboboxEmpty>
                <ComboboxList>
                    {(item) => <ComboboxItem key={item.id} value={item}>{item.name}</ComboboxItem>}
                </ComboboxList>
            </ComboboxContent>
        </Combobox>
    );
}

export default function TeamSettings({
    clubId, behaviours, disabled = false, onSavingChange, onSaveSuccess,
}) {
    const inputPrefix = useId();
    const [error, setError] = useState('');
    const [team, setTeam] = useState(null);
    const [formations, setFormations] = useState([]);
    const [selectedPlayers, setSelectedPlayers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

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

    function changeBehaviour(index, behaviour) {
        setError('');

        setTeam((current) => ({
            ...current,
            slots: current.slots.map((slot, slotIndex) =>
                slotIndex === index
                    ? { ...slot, behaviourId: String(behaviour.id) }
                    : slot
            ),
        }));
    }

    function selectPlayer(slotIndex, player) {
        setError('');

        setTeam((current) => ({
            ...current,
            slots: current.slots.map((slot, index) =>
                index === slotIndex
                    ? {
                        playerId: String(player.id),
                        behaviourId: String(player.behaviorId ?? ''),
                    }
                    : slot
            ),
        }));

        setSelectedPlayers((current) => [
            ...current.filter((item) => item.id !== player.id),
            player,
        ]);
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (disabled || isSaving || !team) return;
        setError('');

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
            onSaveSuccess('Equipo guardado correctamente.');
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

    const slots = team.slots.map((slot, index) => ({slot, index}));
    const selectedFormation = formations.find((formation) => String(formation.id) === team.formation);

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
                        <div className="flex items-center gap-1">
                            <label htmlFor={`${inputPrefix}-formation`} className="text-sm font-medium">
                                Formación
                            </label>
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger
                                        render={<Button variant="ghost" size="icon-xs" className="text-muted-foreground" />}
                                        type="button"
                                        aria-label="Información sobre la formación"
                                        aria-describedby={`${inputPrefix}-formation-help`}
                                    >
                                        <Info aria-hidden="true" />
                                    </TooltipTrigger>
                                    <TooltipContent id={`${inputPrefix}-formation-help`} role="tooltip" align="start">
                                        <div className="space-y-2">
                                            <p>La formación define la posición inicial de los tres titulares en la cancha.</p>
                                            {selectedFormation?.description && (
                                                <p><strong>{selectedFormation.name}</strong> · {selectedFormation.description}</p>
                                            )}
                                            <p>Los cambios se aplican a los próximos partidos. Los partidos ya iniciados conservan su formación.</p>
                                        </div>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        </div>

                        <select
                            id={`${inputPrefix}-formation`}
                            disabled={disabled || isSaving}
                            className={SELECT_CLASSES}
                            value={team.formation}
                            onChange={(event) => {
                                setError('');
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
                    </div>

                    <div className="space-y-6">
                        {LINEUP_GROUPS.map(({name, firstSlot}) => (
                            <section key={name} className="space-y-3">
                                <h3 className="text-sm font-semibold">{name}</h3>
                                <div className="grid grid-cols-3 gap-3">
                                    {slots.slice(firstSlot, firstSlot + 3).map(({slot, index}) => (
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
                                                <label htmlFor={`${inputPrefix}-player-${index}`} className="mb-1 block text-sm font-medium">
                                                    Jugador{' '}<span className="sr-only">del lugar {index + 1}</span>
                                                </label>
                                                <TeamPlayerCombobox
                                                    id={`${inputPrefix}-player-${index}`}
                                                    player={selectedPlayers.find(player => String(player.id) === slot.playerId) ?? null}
                                                    excludedPlayerIds={team.slots.filter((_, slotIndex) => slotIndex !== index).map(other => other.playerId)}
                                                    disabled={disabled || isSaving}
                                                    onSelect={(player) => selectPlayer(index, player)}
                                                />
                                            </div>

                                            <div>
                                                <label htmlFor={`${inputPrefix}-behaviour-${index}`} className="mb-1 block text-sm font-medium">
                                                    Comportamiento{' '}<span className="sr-only">del lugar {index + 1}</span>
                                                </label>

                                                <TeamBehaviourCombobox
                                                    id={`${inputPrefix}-behaviour-${index}`}
                                                    behaviour={behaviours.find(item => String(item.id) === slot.behaviourId) ?? null}
                                                    behaviours={behaviours}
                                                    disabled={disabled || isSaving}
                                                    onSelect={(behaviour) => changeBehaviour(index, behaviour)}
                                                />
                                            </div>
                                        </fieldset>
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>

                    {behaviours.length === 0 && (
                        <p className="text-sm text-destructive">
                            Necesitás comportamientos disponibles.
                        </p>
                    )}

                    <Button
                        type="submit"
                        className="w-full"
                        disabled={isSaving || behaviours.length === 0 || formations.length === 0}
                    >
                        {isSaving ? 'Guardando...' : 'Guardar equipo'}
                    </Button>

                    {error && (
                        <p role="alert" className="text-sm text-destructive">
                            {error}
                        </p>
                    )}
                </form>
            </CardContent>
        </Card>
    );
}
