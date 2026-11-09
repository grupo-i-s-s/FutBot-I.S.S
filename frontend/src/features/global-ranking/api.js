import {request} from '@/api/http';

export function getGlobalRanking(page, signal) {
    const params = new URLSearchParams({page, pageSize: 20});
    return request(`/ranking-global?${params}`, {signal});
}
