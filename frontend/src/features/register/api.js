import { request } from '@/api/http.js'

export function register(email, password, repeatPassword, userName, clubName, avatar) {
    return request('/auth/register', { method: 'POST', body: { email, password, repeatPassword, userName, clubName, avatar } })
}