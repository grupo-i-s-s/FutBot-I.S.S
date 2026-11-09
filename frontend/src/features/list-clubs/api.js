import {request} from '@/api/http.js';

export function getClubs(
    {name = '', page = 1, pageSize = 20} = {},
    signal,
) {
    const params = new URLSearchParams({
        page: String(page),
        pageSize: String(pageSize),
    });

    if (name.trim()) {
        params.set('name', name.trim());
    }

    return request(`/club?${params.toString()}`, {signal});
}