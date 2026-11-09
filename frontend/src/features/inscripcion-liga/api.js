import {request} from '@/api/http.js';
import {getDefaultTeam as getSavedTeam, getPlayersByIds} from '../my-club/api.js';

export async function getDefaultTeam(options) {
    const saved = await getSavedTeam(options);
    const lineup = saved?.lineUp;
    if (!Array.isArray(lineup?.starters) || !Array.isArray(lineup?.substitutes)) {
        throw new Error('Configurá tu equipo guardado antes de inscribirte.');
    }
    const selections = [...lineup.starters, ...lineup.substitutes];
    const ids = selections.map(slot => slot.playerId);
    if (ids.length !== 6 || new Set(ids).size !== ids.length
        || !Number.isInteger(lineup.formationId) || lineup.formationId <= 0
        || selections.some(slot => !Number.isInteger(slot.playerId) || slot.playerId <= 0
            || !Number.isInteger(slot.behaviourId) || slot.behaviourId <= 0)) {
        throw new Error('Revisá los jugadores, la formación y los comportamientos de tu equipo guardado.');
    }
    const players = await getPlayersByIds(ids, options);
    const ordered = ids.map(id => players.find(player => player.id === id));
    if (ordered.some(player => !player)) {
        throw new Error('Hay jugadores de tu equipo guardado que ya no están disponibles.');
    }
    return {clubId: saved.clubId, lineUp: ids, players: ordered};
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
