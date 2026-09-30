import {request} from '@/api/http.js';

export function register(name, power, agility, control, speed, strength) {
    return request('/players', {
        method: 'POST',
        body: {name, power, agility, control, speed, strength}
    });
}


