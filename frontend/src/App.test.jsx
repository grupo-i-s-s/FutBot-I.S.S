import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import App from './App.jsx'

afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
})

function renderRoute(path, response, status = 200) {
    const fetchMock = vi.fn().mockResolvedValue({
        ok: status < 400,
        status,
        json: async () => response,
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
    return fetchMock
}

it('opens the available leagues route and filters through the authenticated API', async () => {
    const fetchMock = renderRoute('/ligas-disponibles', { items: [{
        id: 42, name: 'Liga integrada', registeredCount: 1, maxTeams: 8,
        availableSlots: 7, isMember: true, status: 'open',
    }] })
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument()
    expect(screen.getByText('Tu club ya está inscripto.')).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/leagues')
    expect(fetchMock.mock.calls[0][1].credentials).toBe('same-origin')

    fireEvent.change(screen.getByLabelText('Buscar por nombre'), {
        target: { value: '  Liga integrada  ' },
    })
    fireEvent.submit(screen.getByLabelText('Buscar por nombre').closest('form'))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/leagues?name=Liga+integrada')
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument()
})

it('retains the private league creation route and its request contract', async () => {
    const fetchMock = renderRoute('/crear-liga-privada', {
        message: 'Liga creada exitosamente.',
    }, 201)
    for (const [label, value] of [
        ['Nombre de la liga', 'Liga privada integrada'],
        ['Contraseña', 'clave-de-liga'],
        ['Confirmar Contraseña', 'clave-de-liga'],
        ['Maximo de clubes', '8'],
        ['Fecha y hora de inicio', '2030-01-01T12:00'],
    ]) {
        fireEvent.change(screen.getByLabelText(label), { target: { value } })
    }
    fireEvent.submit(screen.getByRole('button', { name: 'Crear liga' }).closest('form'))
    expect(await screen.findByRole('status')).toHaveTextContent('Liga creada exitosamente.')
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/leagues/private')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({
        name: 'Liga privada integrada', password: 'clave-de-liga',
        min_teams: 3, max_teams: 8,
        start_date: new Date('2030-01-01T12:00').toISOString(),
        round_interval: 'CONTINUOUS',
    })
})

it('retains the lobby route and displays the creator registration from develop', async () => {
    const fetchMock = renderRoute('/leagues/42/lobby', {
        isPrivate: true, minTeams: 3, maxTeams: 8, remainingSlots: 7,
        registeredTeams: 1, isRegistered: true,
        creatorClub: { id: 7, name: 'Club creador' },
        clubs: [{ id: 7, name: 'Club creador' }],
    })
    expect(await screen.findByText('Club creador')).toBeInTheDocument()
    expect(screen.getByText('Privada')).toBeInTheDocument()
    expect(screen.getByText('Creador')).toBeInTheDocument()
    expect(screen.getByText('Tu club está inscripto.')).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/leagues/42/lobby')
})
