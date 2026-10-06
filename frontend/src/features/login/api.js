import {request} from '@/api/http.js';

export function login(email, password) {
    return request('/auth/login', {method: 'POST', body: {email, password}});
}