import {request} from '@/api/http.js';

export function getClubProfile(clubId, options = {}) {
    return request(
        `/club/${encodeURIComponent(clubId)}`,
        options,
    );
}