import {request} from '@/api/http.js';

export function register(name, username, email, clubName, password, passwordConfirmation, avatar) {
    return request('/auth/register', {
        method: 'POST',
        body: {name, username, email, clubName, password, passwordConfirmation, avatar}
    });
}