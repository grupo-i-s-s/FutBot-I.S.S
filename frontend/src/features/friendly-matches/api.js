import {request} from '@/api/http.js';

export function listFriendlyMatches({creatorName = '', page = 1, pageSize = 20} = {}, signal) {
    const query = new URLSearchParams({creatorName, page: String(page), pageSize: String(pageSize)});
    return request(`/friendly-matches?${query}`, {signal});
}

export function listMyFriendlyMatches(signal) {
    return request('/friendly-matches/me', {signal});
}

export function createFriendlyMatch(startDateTime) {
    return request('/friendly-matches', {
        method: 'POST',
        body: {startDateTime: new Date(startDateTime).toISOString()},
    });
}

export function joinFriendlyMatch(matchId) {
    return request(`/friendly-matches/${encodeURIComponent(matchId)}/join`, {
        method: 'POST',
    });
}
