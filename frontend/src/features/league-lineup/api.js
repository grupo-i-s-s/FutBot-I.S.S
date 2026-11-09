import {request} from '../../api/http';
import {listAllPages} from '../../api/pagination';
import {listPlayers} from '../my-club/api';


export function getLeagueLineup(leagueId, options) {
    return request(`/leagues/${leagueId}/lineup`, options);
}


export function updateLeagueLineup(leagueId, body, options = {}) {
    return request(`/leagues/${leagueId}/lineup`, {
        ...options,
        method: 'PUT',
        body,
    });
}


export async function getLineupCatalogs(options) {
    const [players, behaviours, formations] = await Promise.all([
        listAllPages(page => listPlayers({...options, page, pageSize: 100})),
        request('/behaviours?kind=PLAYER', options),
        request('/catalogs/formations', options),
    ]);

    return {
        players,
        behaviours: behaviours.items.filter(
            (behaviour) =>
                behaviour.kind === 'PLAYER' &&
                behaviour.validationStatus === 'VALID',
        ),
        formations: formations.items,
    };
}
