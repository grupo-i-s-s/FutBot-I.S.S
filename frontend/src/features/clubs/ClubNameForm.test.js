import { expect, test } from '@playwright/test'

const initialClub = { id: 7, name: 'Los del barrio', avatar: 'pending', friendlyAvailable: false }
const nameInput = (page) => page.getByRole('textbox', { name: 'Nombre del club', exact: true })
const clubSwitch = (page) => page.getByRole('switch', { name: 'Disponibilidad para amistosos' })

async function mockClub(page, options = {}) {
  const state = { club: { ...initialClub }, patchRequests: [], ...options }
  await page.route('**/api/club/me', async (route) => {
    const request = route.request()
    if (request.method() === 'PATCH') {
      state.patchRequests.push(request)
      if (state.beforePatch) await state.beforePatch()
      if (state.failNetwork) {
        await route.abort('failed')
        return
      }
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

async function openNameEditor(page) {
  await page.goto('/club')
  await page.getByRole('button', { name: 'Cambiar nombre', exact: true }).click()
  await expect(nameInput(page)).toHaveValue(initialClub.name)
}

test('saves only the trimmed name with the session cookie and keeps the confirmed club until success', async ({ page, context }) => {
  await context.addCookies([{ name: 'FutBotSession', value: 'test-session', url: 'http://127.0.0.1:4173', httpOnly: true }])
  let release
  const pending = new Promise((resolve) => { release = resolve })
  const state = await mockClub(page, {
    club: { ...initialClub, friendlyAvailable: true },
    beforePatch: () => pending,
  })
  await openNameEditor(page)
  await nameInput(page).fill('  Club del sur  ')
  await page.screenshot({ path: 'test-results/club-name-desktop.png', fullPage: true })
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect.poll(() => state.patchRequests.length).toBe(1)
  await expect(page.getByRole('heading', { name: initialClub.name, exact: true })).toBeVisible()
  await expect(nameInput(page)).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Cancelar', exact: true })).toBeDisabled()
  await expect(clubSwitch(page)).toBeDisabled()
  await page.keyboard.press('Enter')
  expect(state.patchRequests).toHaveLength(1)
  const request = state.patchRequests[0]
  expect(request.postDataJSON()).toEqual({ name: 'Club del sur' })
  const headers = await request.allHeaders()
  expect(headers['x-futbot-request']).toBe('1')
  expect(headers.cookie).toContain('FutBotSession=test-session')
  expect(headers.authorization).toBeUndefined()
  release()
  await expect(page.getByText('Nombre guardado.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Cambiar nombre', exact: true })).toBeFocused()
  await expect(page.getByRole('heading', { name: 'Club del sur', exact: true })).toBeVisible()
  await expect(clubSwitch(page)).toBeChecked()
  expect(state.club.avatar).toBe(initialClub.avatar)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Club del sur', exact: true })).toBeVisible()
  await expect(clubSwitch(page)).toBeChecked()
})

test('does not save an unchanged name and discards a cancelled draft', async ({ page }) => {
  const state = await mockClub(page)
  await openNameEditor(page)
  const saveButton = page.getByRole('button', { name: 'Guardar nombre', exact: true })
  await expect(saveButton).toBeDisabled()
  await nameInput(page).fill(`  ${initialClub.name}  `)
  await expect(saveButton).toBeDisabled()
  await nameInput(page).fill('Un borrador distinto')
  await expect(saveButton).toBeEnabled()
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click()
  await expect(nameInput(page)).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Cambiar nombre', exact: true })).toBeFocused()
  await expect(page.getByRole('heading', { name: initialClub.name, exact: true })).toBeVisible()
  expect(state.patchRequests).toHaveLength(0)
  await page.getByRole('button', { name: 'Cambiar nombre', exact: true }).click()
  await expect(nameInput(page)).toHaveValue(initialClub.name)
})

for (const { label, value, message } of [
  { label: 'empty', value: '', message: 'Ingresá un nombre para tu club.' },
  { label: 'whitespace-only', value: '   ', message: 'Ingresá un nombre para tu club.' },
  { label: 'longer than 50 characters', value: 'a'.repeat(51), message: 'El nombre no puede superar los 50 caracteres.' },
]) {
  test(`rejects a ${label} name before sending a request`, async ({ page }) => {
    const state = await mockClub(page)
    await openNameEditor(page)
    await nameInput(page).fill(value)
    await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
    await expect(page.getByText(message, { exact: true })).toBeVisible()
    await expect(nameInput(page)).toHaveAttribute('aria-invalid', 'true')
    expect(state.patchRequests).toHaveLength(0)
    await expect(page.getByRole('heading', { name: initialClub.name, exact: true })).toBeVisible()
  })
}

test('accepts exactly 50 Unicode characters after trimming', async ({ page }) => {
  const state = await mockClub(page)
  const nextName = '⚽'.repeat(25) + '😀'.repeat(25)
  await openNameEditor(page)
  await nameInput(page).fill(`  ${nextName}  `)
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('heading', { name: nextName, exact: true })).toBeVisible()
  expect(state.patchRequests).toHaveLength(1)
  expect(state.patchRequests[0].postDataJSON()).toEqual({ name: nextName })
})

test('associates a server validation error with the field and preserves the draft for retry', async ({ page }) => {
  const fieldMessage = 'Revisá el nombre del club.'
  const state = await mockClub(page, {
    patchError: {
      status: 400, code: 'VALIDATION_ERROR', message: 'Revisá los datos ingresados.',
      fields: { name: fieldMessage },
    },
  })
  await openNameEditor(page)
  await nameInput(page).fill('Los del parque')
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'No pudimos confirmar' })).toContainText('Revisá los datos ingresados.')
  await expect(page.getByText(fieldMessage, { exact: true })).toBeVisible()
  await expect(nameInput(page)).toHaveAttribute('aria-invalid', 'true')
  const descriptionIds = (await nameInput(page).getAttribute('aria-describedby')).split(/\s+/)
  const descriptions = await Promise.all(descriptionIds.map((id) => page.locator(`[id="${id}"]`).textContent()))
  expect(descriptions.join(' ')).toContain(fieldMessage)
  await expect(nameInput(page)).toHaveValue('Los del parque')
  await expect(page.getByRole('heading', { name: initialClub.name, exact: true })).toBeVisible()
  state.patchError = null
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Los del parque', exact: true })).toBeVisible()
  await expect(page.getByText('Nombre guardado.', { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('preserves the confirmed name and draft after a network failure and allows retry', async ({ page }) => {
  const state = await mockClub(page, { failNetwork: true })
  await openNameEditor(page)
  await nameInput(page).fill('Club de la plaza')
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Revisá tu conexión.')
  await expect(nameInput(page)).toHaveValue('Club de la plaza')
  await expect(nameInput(page)).toBeEnabled()
  await expect(page.getByRole('heading', { name: initialClub.name, exact: true })).toBeVisible()
  state.failNetwork = false
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Club de la plaza', exact: true })).toBeVisible()
  expect(state.patchRequests).toHaveLength(2)
})

test('refreshes the confirmed name after a failed save while keeping the open draft', async ({ page }) => {
  const state = await mockClub(page, { failNetwork: true })
  await openNameEditor(page)
  await nameInput(page).fill('Mi borrador pendiente')
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Revisá tu conexión.')
  let release
  const pending = new Promise((resolve) => { release = resolve })
  state.beforeGet = () => pending
  state.club = { ...state.club, name: 'Nombre confirmado en el servidor' }
  await page.getByRole('button', { name: 'Volver a consultar', exact: true }).click()
  await expect(nameInput(page)).toBeDisabled()
  await expect(nameInput(page)).toHaveValue('Mi borrador pendiente')
  await expect(page.getByRole('button', { name: 'Cancelar', exact: true })).toBeDisabled()
  await expect(clubSwitch(page)).toBeDisabled()
  release()
  await expect(page.getByRole('heading', { name: state.club.name, exact: true })).toBeVisible()
  await expect(nameInput(page)).toHaveValue('Mi borrador pendiente')
  await expect(nameInput(page)).toBeEnabled()
  await expect(page.getByRole('button', { name: 'Guardar nombre', exact: true })).toBeEnabled()
  expect(state.patchRequests).toHaveLength(1)
})

test('keeps the name draft and confirmed club through a failed refresh and a later retry', async ({ page }) => {
  const state = await mockClub(page, { failNetwork: true })
  await openNameEditor(page)
  await nameInput(page).fill('Borrador que quiero conservar')
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Revisá tu conexión.')
  state.getError = {
    status: 503, code: 'UNAVAILABLE', message: 'Servicio no disponible.', fields: {},
  }
  await page.getByRole('button', { name: 'Volver a consultar', exact: true }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'No pudimos actualizar los datos del club.' })).toBeVisible()
  await expect(nameInput(page)).toHaveValue('Borrador que quiero conservar')
  await expect(nameInput(page)).toBeEnabled()
  await expect(page.getByRole('heading', { name: initialClub.name, exact: true })).toBeVisible()
  state.getError = null
  state.club = { ...state.club, name: 'Club actualizado' }
  await page.getByRole('button', { name: 'Volver a consultar', exact: true }).click()
  await expect(page.getByRole('heading', { name: state.club.name, exact: true })).toBeVisible()
  await expect(nameInput(page)).toHaveValue('Borrador que quiero conservar')
  await expect(nameInput(page)).toBeEnabled()
  await expect(page.getByRole('alert').filter({ hasText: 'No pudimos actualizar los datos del club.' })).toHaveCount(0)
  expect(state.patchRequests).toHaveLength(1)
})

test('removes private data and editing controls when the session expires during a name update', async ({ page }) => {
  await mockClub(page, {
    patchError: { status: 401, code: 'SESSION_INVALID', message: 'Sesión inválida.', fields: {} },
  })
  await openNameEditor(page)
  await nameInput(page).fill('Nombre pendiente')
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Necesitás iniciar sesión' })).toBeVisible()
  await expect(nameInput(page)).toHaveCount(0)
  await expect(clubSwitch(page)).toHaveCount(0)
  await expect(page.getByRole('heading', { name: initialClub.name, exact: true })).toHaveCount(0)
})

test('prevents opening the name editor while availability is being saved', async ({ page }) => {
  let release
  const pending = new Promise((resolve) => { release = resolve })
  const state = await mockClub(page, { beforePatch: () => pending })
  await page.goto('/club')
  await clubSwitch(page).click()
  await expect(page.getByRole('button', { name: 'Cambiar nombre', exact: true })).toBeDisabled()
  await expect.poll(() => state.patchRequests.length).toBe(1)
  expect(state.patchRequests[0].postDataJSON()).toEqual({ friendlyAvailable: true })
  release()
  await expect(clubSwitch(page)).toBeChecked()
  await expect(page.getByRole('button', { name: 'Cambiar nombre', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: 'Cambiar nombre', exact: true }).click()
  await expect(nameInput(page)).toHaveValue(initialClub.name)
})

test('keeps the name editor usable on a narrow screen and renders the saved long name', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 })
  await mockClub(page)
  await openNameEditor(page)
  await nameInput(page).fill('C'.repeat(50))
  await expect(page.getByRole('button', { name: 'Guardar nombre', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/club-name-mobile.png', fullPage: true })
  await page.getByRole('button', { name: 'Guardar nombre', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'C'.repeat(50), exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
