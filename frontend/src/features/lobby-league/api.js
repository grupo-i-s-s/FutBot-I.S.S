import {request} from '@/api/http.js';

export function obtenerLobby(id, signal) {
    return request('/leagues/' + id + '/lobby', {signal});
}

export function obtenerIdentidad(signal) {
    return request('/auth/me', {signal});
}

export function iniciarLiga(id) {
    return request('/leagues/' + id + '/start', {method: 'POST'});
}

export function obtenerFixture(id, signal) {
    return request('/leagues/' + id + '/fixture', {signal});
}

export function abandonarLobby(id) {
    return request('/leagues/' + id + '/leave', {
        method: 'POST',
    });
}
