export function toDraft(lineUp) {
    const selections = lineUp
        ? [...lineUp.starters, ...lineUp.substitutes]
        : Array.from({length: 6}, () => ({
            playerId: '',
            behaviourId: '',
        }));

    return {
        formationId: String(lineUp?.formationId ?? ''),
        slots: selections.map((slot) => ({
            playerId: String(slot.playerId),
            behaviourId: String(slot.behaviourId),
        })),
    };
}


export function validateDraft(draft, catalogs) {
    if (!catalogs.formations.some(
        (item) => String(item.id) === draft.formationId,
    )) {
        return 'Elegí una formación disponible.';
    }

    const ids = draft.slots.map((slot) => slot.playerId);

    if (
        ids.length !== 6 ||
        ids.some((id) =>
            !catalogs.players.some((player) => String(player.id) === id),
        )
    ) {
        return 'Completá los seis lugares con jugadores de tu club.';
    }

    if (new Set(ids).size !== 6) {
        return 'Los seis jugadores deben ser distintos.';
    }

    if (draft.slots.some((slot) =>
        !catalogs.behaviours.some(
            (item) => String(item.id) === slot.behaviourId,
        ),
    )) {
        return 'Elegí un comportamiento validado para cada jugador.';
    }

    return '';
}


export function changeSlot(draft, index, field, value, catalogs) {
    const slots = draft.slots.map((slot) => ({...slot}));

    if (field === 'playerId') {
        if (slots[index].playerId === value) return draft;

        const otherIndex = value
            ? slots.findIndex((slot, position) =>
                position !== index && slot.playerId === value,
            )
            : -1;

        if (otherIndex !== -1) {
            [slots[index], slots[otherIndex]] = [
                slots[otherIndex],
                slots[index],
            ];
        } else {
            const player = catalogs.players.find(
                (item) => String(item.id) === value,
            );
            const behaviourId = String(player?.behaviorId ?? '');
            const available = catalogs.behaviours.some(
                (item) => String(item.id) === behaviourId,
            );

            slots[index] = {
                playerId: value,
                behaviourId: available ? behaviourId : '',
            };
        }
    } else {
        slots[index] = {...slots[index], [field]: value};
    }

    return {...draft, slots};
}


export function toPayload(draft, expectedVersion) {
    const selections = draft.slots.map((slot) => ({
        playerId: Number(slot.playerId),
        behaviourId: Number(slot.behaviourId),
    }));

    return {
        formationId: Number(draft.formationId),
        starters: selections.slice(0, 3),
        substitutes: selections.slice(3, 6),
        expectedVersion,
    };
}