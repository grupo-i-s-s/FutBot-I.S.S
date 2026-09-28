export async function login(email, password) {
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json',  'X-FutBot-Request': '1',},
        body: JSON.stringify({email,password, }),
    })
    return response
}