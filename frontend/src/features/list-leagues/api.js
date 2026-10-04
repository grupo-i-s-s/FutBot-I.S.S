import { request } from '@/api/http.js'

export function getLeagues(name = '', signal) {
    const params = new URLSearchParams()

    if (name.trim()) {
        params.set('name', name.trim())
    }

    const query = params.toString()
    const path = query ? `/leagues?${query}` : '/leagues'

    return request(path, { signal })
}