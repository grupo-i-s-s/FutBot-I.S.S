import {request} from '@/api/http.js';

export function validateMatchId(matchId) {
    const id = Number(matchId);
    if (!Number.isSafeInteger(id) || id <= 0) throw new Error('ID de partido inválido.');
    return id;
}

export function getMatchSnapshot(matchId, signal) {
    return request(`/matches/${validateMatchId(matchId)}`, {signal});
}

export function matchStreamUrl(matchId) {
    const id = validateMatchId(matchId);

    const url = new URL(`/api/matches/${id}/stream`, window.location.origin);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';

    return url.toString();
}

export function changeBehaviour(matchId, playerId, behaviourId) {
    const id = validateMatchId(matchId);
    
    return request(`/matches/${id}/live_request`, {
        method: 'POST',
        body:{
            player_id: playerId,
            behaviour_id: behaviourId
        }
    });
}

export function activateMatchDt(matchId, active) {
    const id = validateMatchId(matchId);
    return request(`/matches/${id}/dt`, {
        method: 'POST',
        body: { dt_active: active }
    });
}