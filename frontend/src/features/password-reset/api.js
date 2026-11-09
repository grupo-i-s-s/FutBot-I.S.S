import {request} from '@/api/http.js';

export function requestPasswordReset(email) {
    return request('/auth/password-reset/request', {
        method: 'POST',
        body: {email},
    });
}

export function confirmPasswordReset(email, code, newPassword, passwordConfirmation) {
    return request('/auth/password-reset/confirm', {
        method: 'POST',
        body: {email, code, newPassword, passwordConfirmation},
    });
}