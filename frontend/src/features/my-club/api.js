import { request } from '../../api/http';

// Endpoints según docs/api_endpoints.md.
export function getMyClub(options) {
    return request('/club/me', options);
}

export function listPlayers({ page = 1, limit = 9, search, ...options } = {}) {
    const params = new URLSearchParams({ page, limit });
    if (search?.trim()) params.set('search', search.trim());
    return request(`/players?${params.toString()}`, options);
}

export function getPlayersByIds(ids, options) {
    const params = new URLSearchParams();
    ids.forEach((id) => params.append('ids', id));
    return request(`/players/by-ids?${params}`, options);
}

export function listBehaviours(options) {
    return request('/behaviours', options);
}

export function assignPlayerBehaviour(playerId, behaviourId) {
    return request(`/players/${playerId}/behaviour`, {
        method: 'PATCH',
        body: { behaviourId },
    });
}

export function updateMyClub(changes) {
    return request('/club/me', {
        method: 'PATCH',
        body: changes,
    });
}

export function listMyLeagues(options) {
    return request('/club/me/leagues', options);
}

export async function getDefaultTeam(options) {
    try {
        return await request('/team/default', options);
    } catch (error) {
        if (
            error.status === 409 &&
            error.code === 'ACCOUNT_INCOMPLETE'
        ) {
            return null;
        }

        throw error;
    }
}

export function getFormations(options) {
    return request('/catalogs/formations', options);
}

export function updateDefaultTeam(lineUp) {
    return request('/team/default', {
        method: 'PUT',
        body: lineUp,
    });
}
