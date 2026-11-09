import {request} from '@/api/http.js';

export function validateMatchId(matchId) {
    const id = Number(matchId);
    if (!Number.isSafeInteger(id) || id <= 0) throw new Error('ID de partido inválido.');
    return id;
}

export function getMatchSnapshot(matchId, signal) {
    return request(`/matches/${validateMatchId(matchId)}`, {signal});
}

export function planSubstitution(matchId, body, signal) {
    return request(`/matches/${validateMatchId(matchId)}/planned-substitution`, {method: 'PUT', body, signal});
}

export function requestSubstitution(matchId, body, signal) {
    return request(`/matches/${validateMatchId(matchId)}/substitutions`, {method: 'POST', body, signal});
}

export function matchStreamUrl(matchId) {
    const id = validateMatchId(matchId);

    const url = new URL(`/api/matches/${id}/stream`, window.location.origin);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';

    return url.toString();
}

export function changeBehaviour(matchId, playerId, behaviourId) {
    const id = validateMatchId(matchId);

    return request(`/matches/${id}/live-requests`, {
        method: 'POST',
        body: {playerId, behaviourId},
    });
}

export function activateMatchDt(matchId, active) {
    const id = validateMatchId(matchId);
    return request(`/matches/${id}/dt`, {
        method: 'POST',
        body: {dtActive: active},
    });
}
