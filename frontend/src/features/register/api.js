import { request } from '@/api/http.js';

export function register(email, clubName, password, passwordConfirmation) {
    return request('/auth/register', {
        method: 'POST',
        body: { email, clubName, password, passwordConfirmation }
    });
}

export function verifyEmail(email, code, registration) {
    return request('/auth/verify-email', {
        method: 'POST',
        body: { email, code, registration },
    });
}

export function resendVerification(email) {
    return request('/auth/resend-verification', {
        method: 'POST',
        body: { email },
    });
}
