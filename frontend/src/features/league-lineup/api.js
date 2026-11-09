import {request} from '../../api/http';


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


async function listAllPlayers(options) {
    const players = new Map();
    let page = 1;

    while (true) {
        const response = await request(
            `/players?page=${page}&limit=100`,
            options,
        );

        response.items.forEach((player) => players.set(player.id, player));

        if (page >= response.totalPages) {
            return [...players.values()];
        }

        page += 1;
    }
}


export async function getLineupCatalogs(options) {
    const [players, behaviours, formations] = await Promise.all([
        listAllPlayers(options),
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