import {getSessionRevision, request} from '../../api/http';
import { notifyClubUpdated } from './clubEvents';


export function getMyClub(options) {
    return request('/clubs/me', options);
}

export function listPlayers({ page = 1, pageSize = 9, search, ...options } = {}) {
    const params = new URLSearchParams({ page, pageSize });
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

export function listDtBehaviours(options) {
    return request('/clubs/me/dt/behaviours', options);
}

export function updateDtSettings(body) {
    return request('/clubs/me/dt', { method: 'PATCH', body });
}

export async function updateMyClub(changes) {
    const revision = getSessionRevision();
    const updatedClub = await request('/clubs/me', {
        method: 'PATCH',
        body: changes,
    });
    if (revision === getSessionRevision()) notifyClubUpdated(updatedClub);
    return updatedClub;
}

export function listMyLeagues(options) {
    return request('/clubs/me/leagues', options);
}

export async function getDefaultTeam(options) {
    try {
        return await request('/clubs/me/default-team', options);
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
    return request('/clubs/me/default-team', {
        method: 'PUT',
        body: lineUp,
    });
}
