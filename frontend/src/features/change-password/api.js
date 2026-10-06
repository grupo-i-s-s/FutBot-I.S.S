import {request} from '@/api/http.js';

export function changePassword(oldPassword, newPassword) {
    return request('/auth/change-password', {
        method: 'POST',
        body: {oldPassword, newPassword},
    });
}