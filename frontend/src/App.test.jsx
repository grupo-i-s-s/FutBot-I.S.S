import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {createMemoryRouter, MemoryRouter, RouterProvider} from 'react-router';
import App from './App.jsx';

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function renderRoute(path, response, status = 200) {
    const fetchMock = vi.fn(async (url) => {
        let body = response;
        let responseStatus = status;

        if (url === '/api/club/me') {
            body = {id: 7, name: 'Club de prueba', avatar: 'avatar-01.png'};
            responseStatus = 200;
        } else if (url === '/api/auth/me') {
            body = {clubId: 7};
            responseStatus = 200;
        } else if (path === '/crear-liga-privada' && url === '/api/leagues/42/lobby') {
            body = {
                id: 42, name: 'Liga privada integrada', isPrivate: true,
                status: 'open', minTeams: 3, maxTeams: 8,
                registeredTeams: 1, remainingSlots: 7, isRegistered: true,
                creatorClubId: 7,
                creatorClub: {id: 7, name: 'Club de prueba'},
                clubs: [{id: 7, name: 'Club de prueba'}],
            };
            responseStatus = 200;
        }

        return {
            ok: responseStatus < 400,
            status: responseStatus,
            json: async () => body,
        };
    });
    vi.stubGlobal('fetch', fetchMock);
    const router = createMemoryRouter(
        [{path: '*', element: <App/>}],
        {initialEntries: [path]},
    );
    render(<RouterProvider router={router}/>);
    return {fetchMock, router};
}

it('opens the available leagues route and filters through the authenticated API', async () => {
    const {fetchMock} = renderRoute('/ligas-disponibles', {
        items: [{
            id: 42, name: 'Liga integrada', registeredCount: 1, maxTeams: 8,
            availableSlots: 7, isMember: true, status: 'open',
        }]
    });
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument();
    expect(screen.getByText('Tu club ya está inscripto.')).toBeInTheDocument();
    const initialRequest = fetchMock.mock.calls.find(([url]) => url === '/api/leagues');
    expect(initialRequest).toBeDefined();
    expect(initialRequest[1].credentials).toBe('same-origin');

    fireEvent.change(screen.getByLabelText('Buscar por nombre'), {
        target: {value: '  Liga integrada  '},
    });
    fireEvent.submit(screen.getByLabelText('Buscar por nombre').closest('form'));
    await waitFor(() => expect(fetchMock.mock.calls.some(
        ([url]) => url === '/api/leagues?name=Liga+integrada'
    )).toBe(true));
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument();
});

it('retains the private league creation route and its request contract', async () => {
    const {fetchMock, router} = renderRoute('/crear-liga-privada', {
        leagueId: 42,
        message: 'Liga creada exitosamente.',
    }, 201);
    for (const [label, value] of [
        ['Nombre de la liga', 'Liga privada integrada'],
        ['Contraseña', 'clave-de-liga'],
        ['Confirmar Contraseña', 'clave-de-liga'],
        ['Maximo de clubes', '8'],
        ['Fecha y hora de inicio', '2030-01-01T12:00'],
    ]) {
        fireEvent.change(screen.getByLabelText(label), {target: {value}});
    }
    fireEvent.submit(screen.getByRole('button', {name: 'Crear liga'}).closest('form'));
    await waitFor(() => expect(router.state.location.pathname).toBe('/leagues/42/lobby'));
    const [url, options] = fetchMock.mock.calls.find(
        ([requestUrl, requestOptions]) => requestUrl === '/api/leagues/private' && requestOptions.method === 'POST'
    );
    expect(url).toBe('/api/leagues/private');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
        name: 'Liga privada integrada', password: 'clave-de-liga',
        min_teams: 3, max_teams: 8,
        start_date: new Date('2030-01-01T12:00').toISOString(),
        round_interval: 'CONTINUOUS',
    });
});

it('retains the lobby route and displays the creator registration from develop', async () => {
    const {fetchMock} = renderRoute('/leagues/42/lobby', {
        isPrivate: true, minTeams: 3, maxTeams: 8, remainingSlots: 7,
        registeredTeams: 1, isRegistered: true,
        creatorClub: {id: 7, name: 'Club creador'},
        clubs: [{id: 7, name: 'Club creador'}],
    });
    expect(await screen.findByText('Club creador')).toBeInTheDocument();
    expect(screen.getByText('Privada')).toBeInTheDocument();
    expect(screen.getByText('Creador')).toBeInTheDocument();
    expect(screen.getByText('Tu club está inscripto.')).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/leagues/42/lobby')).toBe(true);
});

it.each([false, true])('joins a league from the listing and opens its lobby (private: %s)', async (isPrivate) => {
    let joined = false;
    const ids = [56, 51, 55, 52, 54, 53];
    const slots = ids.map(playerId => ({playerId, behaviourId: 7}));
    const players = [51, 52, 53, 54, 55, 56].map(id => ({
        id, name: id === 51 ? 'Jugadora del club' : `Jugador ${id}`,
    }));
    const league = {
        id: 42, name: 'Liga para inscripción', isPrivate, isMember: false,
        registeredCount: 1, availableSlots: 7, maxTeams: 8, status: 'open',
        startDatetime: '2000-01-01T00:00:00Z',
    };
    const fetchMock = vi.fn(async (url, options) => {
        let response;
        if (url === '/api/leagues') response = {items: [league]};
        else if (url === '/api/auth/me') response = {clubId: 8};
        else if (url === '/api/team/default') response = {
            clubId: 8, lineUp: {formationId: 2, starters: slots.slice(0, 3), substitutes: slots.slice(3)},
        };
        else if (url.startsWith('/api/players/by-ids?')) response = players;
        else if (url === '/api/leagues/42/join') {
            joined = true;
            response = {message: 'Te has unido a la liga exitosamente.'};
        } else if (url === '/api/leagues/42/lobby') response = {
            ...league, minTeams: 3, isRegistered: joined,
            remainingSlots: joined ? 6 : 7, registeredTeams: joined ? 2 : 1,
            creatorClub: {id: 7, name: 'Club creador'},
            clubs: joined ? [{id: 7, name: 'Club creador'}, {id: 8, name: 'Mi club'}] : [],
        };
        else throw new Error(`Unexpected request: ${url}`);
        return {ok: true, status: options.method === 'POST' ? 201 : 200, json: async () => response};
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<MemoryRouter initialEntries={['/ligas-disponibles']}><App/></MemoryRouter>);
    fireEvent.click(await screen.findByRole('link', {name: 'Inscribirse'}));
    expect(await screen.findByText('Jugadora del club')).toBeInTheDocument();
    if (isPrivate) {
        fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: 'clave-de-liga'}});
    }
    fireEvent.click(screen.getByRole('button', {name: 'Confirmar inscripción'}));
    expect(await screen.findByText('Tu club está inscripto.')).toBeInTheDocument();
    expect(screen.getByText('Mi club', {selector: '.player-name'})).toBeInTheDocument();
    const [, options] = fetchMock.mock.calls.find(([url]) => url.endsWith('/join'));
    expect(JSON.parse(options.body)).toEqual({
        clubId: 8, lineUp: ids, ...(isPrivate ? {accessCode: 'clave-de-liga'} : {}),
    });
});
