import { expect, test } from '@playwright/test'

const initialClub = { id: 7, name: 'Los del barrio', avatar: 'pending', friendlyAvailable: false }
const clubSwitch = (page) => page.getByRole('switch', { name: 'Disponibilidad para amistosos' })

async function mockClub(page, options = {}) {
  const state = { club: { ...initialClub }, patchRequests: [], ...options }
  await page.route('**/api/club/me', async (route) => {
    const request = route.request()
    if (request.method() === 'PATCH') {
      state.patchRequests.push(request)
      if (state.beforePatch) await state.beforePatch()
      if (state.patchError) {
        await route.fulfill({ status: state.patchError.status, json: { error: state.patchError } })
        return
      }
      state.club = { ...state.club, ...request.postDataJSON() }
    } else {
      if (state.beforeGet) await state.beforeGet()
      if (state.getError) {
        await route.fulfill({ status: state.getError.status, json: { error: state.getError } })
        return
      }
    }
    await route.fulfill({ json: state.club })
  })
  return state
}

test('shows loading, the authenticated club and unavailable module entries', async ({ page }) => {
  let release
  const pending = new Promise((resolve) => { release = resolve })
  await mockClub(page, { beforeGet: () => pending })
  await page.goto('/club')
  await expect(page.getByText('Cargando tu club…')).toBeVisible()
  release()
  await expect(page.getByRole('heading', { name: initialClub.name })).toBeVisible()
  await expect(clubSwitch(page)).not.toBeChecked()
  await expect(page.getByText('Próximamente', { exact: true })).toHaveCount(5)
  await expect(page.getByRole('link')).toHaveCount(0)
  await expect(page.getByText('Activá la disponibilidad', { exact: false })).toBeVisible()
  await expect(page.getByText('No cancela amistosos', { exact: false })).toBeVisible()
})

test('saves only availability with session cookie and CSRF header, then reloads persisted state', async ({ page, context }) => {
  await context.addCookies([{ name: 'FutBotSession', value: 'test-session', url: 'http://127.0.0.1:4173', httpOnly: true }])
  let release
  const pending = new Promise((resolve) => { release = resolve })
  const state = await mockClub(page, { beforePatch: () => pending })
  await page.goto('/club')
  await clubSwitch(page).click()
  await expect(clubSwitch(page)).toBeDisabled()
  await expect(clubSwitch(page)).not.toBeChecked()
  await expect(page.getByText('Guardando disponibilidad…')).toBeVisible()
  await expect.poll(() => state.patchRequests.length).toBe(1)
  const request = state.patchRequests[0]
  expect(request.postDataJSON()).toEqual({ friendlyAvailable: true })
  const headers = await request.allHeaders()
  expect(headers['x-futbot-request']).toBe('1')
  expect(headers.cookie).toContain('FutBotSession=test-session')
  expect(headers.authorization).toBeUndefined()
  release()
  await expect(clubSwitch(page)).toBeChecked()
  await expect(page.getByText('Disponibilidad guardada.')).toBeVisible()
  await page.reload()
  await expect(clubSwitch(page)).toBeChecked()
  await clubSwitch(page).focus()
  await page.keyboard.press('Space')
  await expect(clubSwitch(page)).not.toBeChecked()
  expect(state.club.name).toBe(initialClub.name)
  expect(state.club.avatar).toBe(initialClub.avatar)
})

test('preserves the confirmed value after a rejected save and allows retry', async ({ page }) => {
  const state = await mockClub(page, { patchError: { status: 403, code: 'CSRF_INVALID', message: 'Solicitud no permitida.', fields: {} } })
  await page.goto('/club')
  await clubSwitch(page).click()
  await expect(page.getByRole('alert')).toContainText('No pudimos confirmar el cambio.')
  await expect(clubSwitch(page)).not.toBeChecked()
  await expect(clubSwitch(page)).toBeEnabled()
  state.patchError = null
  await clubSwitch(page).click()
  await expect(clubSwitch(page)).toBeChecked()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('recovers a read error without showing it as an empty club', async ({ page }) => {
  const state = await mockClub(page, { getError: { status: 503, code: 'UNAVAILABLE', message: 'Servicio no disponible.', fields: {} } })
  await page.goto('/club')
  await expect(page.getByRole('alert')).toContainText('No pudimos cargar tu club')
  await expect(clubSwitch(page)).toHaveCount(0)
  state.getError = null
  await page.getByRole('button', { name: 'Volver a intentar' }).click()
  await expect(page.getByRole('heading', { name: initialClub.name })).toBeVisible()
})

test('reports network failure and can consult the latest state again', async ({ page }) => {
  let failPatch = true
  await page.route('**/api/club/me', async (route) => {
    if (route.request().method() === 'PATCH' && failPatch) {
      await route.abort('failed')
    } else {
      await route.fulfill({ json: { ...initialClub, friendlyAvailable: !failPatch } })
    }
  })
  await page.goto('/club')
  await clubSwitch(page).click()
  await expect(page.getByRole('alert')).toContainText('Revisá tu conexión.')
  await expect(clubSwitch(page)).not.toBeChecked()
  failPatch = false
  await page.getByRole('button', { name: 'Volver a consultar' }).click()
  await expect(clubSwitch(page)).toBeChecked()
})

test('a 401 requests sign-in without exposing club controls', async ({ page }) => {
  await mockClub(page, { getError: { status: 401, code: 'SESSION_INVALID', message: 'Sesión inválida.', fields: {} } })
  await page.goto('/club')
  await expect(page.getByRole('heading', { name: 'Necesitás iniciar sesión' })).toBeVisible()
  await expect(clubSwitch(page)).toHaveCount(0)
  await expect(page.getByRole('heading', { name: initialClub.name })).toHaveCount(0)
})

test('an expired session during save removes private data and actions', async ({ page }) => {
  await mockClub(page, { patchError: { status: 401, code: 'SESSION_INVALID', message: 'Sesión inválida.', fields: {} } })
  await page.goto('/club')
  await clubSwitch(page).click()
  await expect(page.getByRole('heading', { name: 'Necesitás iniciar sesión' })).toBeVisible()
  await expect(clubSwitch(page)).toHaveCount(0)
  await expect(page.getByRole('heading', { name: initialClub.name })).toHaveCount(0)
})

test('distinguishes an incomplete account from an unauthenticated visitor', async ({ page }) => {
  await mockClub(page, { getError: { status: 409, code: 'ACCOUNT_INCOMPLETE', message: 'No hay club asociado.', fields: {} } })
  await page.goto('/club')
  await expect(page.getByRole('heading', { name: 'Tu cuenta todavía no tiene un club' })).toBeVisible()
  await expect(clubSwitch(page)).toHaveCount(0)
})

test('rejects malformed data instead of displaying an invented availability', async ({ page }) => {
  await mockClub(page, { club: { ...initialClub, friendlyAvailable: 'false' } })
  await page.goto('/club')
  await expect(page.getByRole('alert')).toContainText('No pudimos interpretar los datos del club.')
  await expect(clubSwitch(page)).toHaveCount(0)
})

test('handles an HTML server error', async ({ page }) => {
  await page.route('**/api/club/me', (route) => route.fulfill({ status: 502, contentType: 'text/html', body: '<h1>Bad gateway</h1>' }))
  await page.goto('/club')
  await expect(page.getByRole('alert')).toContainText('El servidor no pudo completar la solicitud.')
})

test('reports a stalled request and allows retry', async ({ page }) => {
  await page.clock.install()
  await mockClub(page, { beforeGet: () => new Promise(() => {}) })
  await page.goto('/club')
  await expect(page.getByText('Cargando tu club…')).toBeVisible()
  await page.clock.fastForward(10001)
  await expect(page.getByRole('alert')).toContainText('El servidor tardó demasiado en responder.')
  await expect(page.getByRole('button', { name: 'Volver a intentar' })).toBeEnabled()
})

test('fits a narrow screen with a long club name and can update availability', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 })
  await mockClub(page, { club: { ...initialClub, name: 'ClubDePruebaConUnNombreMuyLargoSinEspaciosParaComprobarElDiseño' } })
  await page.goto('/club')
  await expect(clubSwitch(page)).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await clubSwitch(page).click()
  await expect(clubSwitch(page)).toBeChecked()
  await page.screenshot({ path: 'test-results/my-club-mobile.png', fullPage: true })
})

test('renders configured module destinations and follows their links', async ({ page }) => {
  await mockClub(page)
  const modules = [
    ['Plantel', '/test-players'], ['Mi equipo', '/test-team'],
    ['Comportamientos', '/test-behaviours'], ['Ligas', '/test-leagues'],
    ['Amistosos', '/test-friendly-matches'],
  ]
  for (const [name, path] of modules) {
    await page.route(`**${path}`, (route) => route.fulfill({ contentType: 'text/html', body: `<h1>${name}</h1>` }))
    await page.goto('/tests/fixtures/club.html')
    await page.getByRole('link', { name: new RegExp(name) }).click()
    await expect(page).toHaveURL(new RegExp(`${path}$`))
    await expect(page.getByRole('heading', { name })).toBeVisible()
  }
})

test('uses the login destination supplied by the auth integration', async ({ page }) => {
  await mockClub(page, { getError: { status: 401, code: 'SESSION_INVALID', message: 'Sesión inválida.', fields: {} } })
  await page.route('**/test-login', (route) => route.fulfill({ contentType: 'text/html', body: '<h1>Ingreso de prueba</h1>' }))
  await page.goto('/tests/fixtures/club.html')
  await page.getByRole('link', { name: 'Iniciar sesión', exact: true }).click()
  await expect(page).toHaveURL(/\/test-login$/)
})

test('keeps the existing development page and adds access to My club', async ({ page }) => {
  await mockClub(page)
  await page.route('**/api/health/ready', (route) => route.fulfill({ json: { status: 'ok', database: 'ok' } }))
  await page.goto('/')
  await page.getByRole('link', { name: 'Ir a Mi club' }).click()
  await expect(page).toHaveURL(/\/club$/)
  await expect(page.getByRole('heading', { name: initialClub.name })).toBeVisible()
  await page.screenshot({ path: 'test-results/my-club-desktop.png', fullPage: true })
})
