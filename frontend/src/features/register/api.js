import {request} from '@/api/http.js';

export function register(email, clubName, password, passwordConfirmation) {
    return request('/auth/register', {
        method: 'POST',
        body: {email, clubName, password, passwordConfirmation}
    });
}