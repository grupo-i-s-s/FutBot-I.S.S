import {request} from '@/api/http.js';

export function obtenerLobby(id, signal) {
    return request('/leagues/' + id + '/lobby', {signal});
}

export function abandonarLobby(id) {
    return request('/leagues/' + id + '/leave', {
        method: 'POST',
    });
}

export function getLeagueRanking(leagueId, signal) {
    return request('/leagues/' + leagueId + '/ranking', { signal });
}