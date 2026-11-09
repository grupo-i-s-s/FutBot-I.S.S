import { request } from '../../api/http';

export function getBehaviour(behaviourId, options) {
    return request(`/behaviours/${behaviourId}`, options);
}

export function listBehaviours(options) {
    return request('/behaviours', options);
}

export function deleteBehaviour(behaviourId) {
    return request(`/behaviours/${behaviourId}`, {
        method: 'DELETE'
    });
}

export function createBehaviourTestMatch() {
    return request('/friendly-matches/behaviour-test', {
        method: 'POST',
    });
}

export function getBehaviourUsage(behaviourId, options) {
    return request(`/behaviours/${behaviourId}/usage`, options);
}

export function updateBehaviour(
    behaviourId,
    {name, code, expectedVersion},
) {
    return request(`/behaviours/${behaviourId}`, {
        method: 'PUT',
        body: {name, code, expectedVersion},
    });
}