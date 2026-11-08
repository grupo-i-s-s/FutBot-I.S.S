import {request} from '@/api/http.js';
import {getDefaultTeam as getSavedTeam, getFormations, getPlayersByIds, listBehaviours} from '../my-club/api.js';

function isPositiveInteger(value) {
    return Number.isSafeInteger(value) && value > 0;
}

export async function getDefaultTeam(options) {
    const saved = await getSavedTeam(options);
    const lineUp = saved?.lineUp;
    if (!lineUp) {
        throw new Error('Configurá tu equipo guardado antes de inscribirte.');
    }
    const {formationId, starters, substitutes} = lineUp;
    if (!isPositiveInteger(saved.clubId)) {
        throw new Error('No se pudo identificar el club de tu equipo guardado.');
    }
    if (!isPositiveInteger(formationId)) {
        throw new Error('Revisá la formación de tu equipo guardado.');
    }
    if (!Array.isArray(starters) || starters.length !== 3
        || !Array.isArray(substitutes) || substitutes.length !== 3) {
        throw new Error('Tu equipo guardado debe tener tres titulares y tres suplentes.');
    }
    const slots = [...starters, ...substitutes];
    const playerIds = slots.map(slot => slot?.playerId);
    if (playerIds.some(id => !isPositiveInteger(id)) || new Set(playerIds).size !== playerIds.length) {
        throw new Error('Elegí seis jugadores distintos para tu equipo guardado.');
    }
    if (slots.some(slot => !isPositiveInteger(slot.behaviourId))) {
        throw new Error('Elegí un comportamiento para cada jugador de tu equipo guardado.');
    }

    const [players, formations, behaviours] = await Promise.all([
        getPlayersByIds(playerIds, options),
        getFormations(options),
        listBehaviours(options),
    ]);
    const formation = formations.items.find(item => item.id === formationId);
    if (!formation) {
        throw new Error('La formación de tu equipo guardado ya no está disponible.');
    }
    const playersById = new Map(players.map(player => [player.id, player]));
    const behavioursById = new Map(behaviours.items
        .filter(behaviour => behaviour.kind === 'PLAYER' && behaviour.validationStatus === 'VALID')
        .map(behaviour => [behaviour.id, behaviour]));

    function describeSlot({playerId, behaviourId}) {
        const player = playersById.get(playerId);
        if (!player) {
            throw new Error('Hay jugadores de tu equipo guardado que ya no están disponibles.');
        }
        const behaviour = behavioursById.get(behaviourId);
        if (!behaviour) {
            throw new Error(`El comportamiento guardado para ${player.name} ya no está disponible.`);
        }
        return {id: playerId, name: player.name, behaviourName: behaviour.name};
    }

    return {
        clubId: saved.clubId,
        lineUp,
        formationName: formation.name,
        starters: starters.map((slot, index) => ({...describeSlot(slot), position: formation.slots[index].label})),
        substitutes: substitutes.map(describeSlot),
    };
}

export function joinLeague(leagueId, clubId, lineUp, accessCode) {
    return request(`/leagues/${leagueId}/join`, {
        method: 'POST',
        body: {
            clubId,
            lineUp,
            ...(accessCode ? {accessCode} : {}),
        },
    });
}

export function getLeagueLobby(leagueId, options) {
    return request(`/leagues/${leagueId}/lobby`, options);
}
