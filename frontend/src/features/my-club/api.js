import {request} from '../../api/http';
import {notifyClubUpdated} from './clubEvents';

// Endpoints según docs/api_endpoints.md.
export function getMyClub(options) {
    return request('/club/me', options);
}

export function listPlayers(options) {
    return request('/players', options);
}

export function listBehaviours(options) {
    return request('/behaviours', options);
}

export function assignPlayerBehaviour(playerId, behaviourId) {
    return request(`/players/${playerId}/behaviour`, {
        method: 'PATCH',
        body: {behaviourId},
    });
}

export async function updateMyClub(changes) {
    const updatedClub = await request('/club/me', {
        method: 'PATCH',
        body: changes,
    });
    notifyClubUpdated(updatedClub);
    return updatedClub;
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
