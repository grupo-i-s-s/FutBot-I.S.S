import {request} from '@/api/http.js';

export async function getLeagues(name = '', signal) {
    const params = new URLSearchParams();

    if (name.trim()) {
        params.set('name', name.trim());
    }

    const query = params.toString();
    const path = query ? `/leagues?${query}` : '/leagues';

    const response = await request(path, {signal});

    return {
        ...response,
        items: response.items.map((league) => ({
            ...league,
            canJoin:
                !league.isMember &&
                league.status === 'open' &&
                league.availableSlots > 0,
        })),
    };
}
