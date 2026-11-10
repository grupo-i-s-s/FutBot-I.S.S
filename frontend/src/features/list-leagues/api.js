import {request} from '@/api/http.js';
import {listAllPages} from '@/api/pagination.js';

export async function getLeagues(name = '', signal) {
    const search = name.trim();
    const leagues = await listAllPages(page => {
        const params = new URLSearchParams({page, pageSize: 100});
        if (search) params.set('name', search);
        return request(`/leagues?${params}`, {signal});
    });

    return {
        items: leagues.map((league) => ({
            ...league,
            canJoin:
                !league.isMember &&
                league.status === 'open' &&
                league.availableSlots > 0,
        })),
    };
}
