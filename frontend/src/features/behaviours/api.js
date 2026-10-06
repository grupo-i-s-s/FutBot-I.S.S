import {request} from '../../api/http';

export function getBehaviour(behaviourId, options) {
    return request(`/behaviours/${behaviourId}`, options);
}