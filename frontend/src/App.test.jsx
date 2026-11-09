import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {MemoryRouter, useLocation} from 'react-router';
import App from './App.jsx';

const club = {id: 8, name: 'Club de pruebas', avatar: 'avatar-01.png', friendlyAvailable: true};
const invalidSession = {error: {code: 'SESSION_INVALID', message: 'La sesión venció.'}};

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function jsonResponse(body, status = 200) {
    return {
        ok: status < 400,
        status,
        json: async () => body,
    };
}

function CurrentPath() {
    const {pathname} = useLocation();
    return <span hidden data-testid="current-path">{pathname}</span>;
}

function renderRoute(path, responses = {}, getClub = () => jsonResponse(club)) {
    const fetchMock = vi.fn(async (url, options) => {
        if (url === '/api/club/me') return getClub();
        const respond = responses[url];
        if (!respond) throw new Error(`Unexpected request: ${url}`);
        return respond(options);
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<MemoryRouter initialEntries={[path]}><App/><CurrentPath/></MemoryRouter>);
    return fetchMock;
}

it.each([
    '/ligas-disponibles', '/liga-cancelada', '/clubes', '/club/42',
    '/crear-comportamiento-dt', '/leagues/42/lineup',
])('redirects anonymous visits to %s to /', async (path) => {
    const fetchMock = renderRoute(path, {}, () => jsonResponse(invalidSession, 401));

    expect(await screen.findByRole('heading', {name: /inicio de sesión/i})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/$/);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/api/club/me']);
    const nav = within(screen.getByRole('navigation'));
    expect(nav.getByRole('link', {name: 'Iniciar sesión'})).toBeInTheDocument();
    expect(nav.getByRole('link', {name: 'Registrarse'})).toHaveAttribute('href', '/registro');
    expect(nav.queryByRole('link', {name: 'Mi club'})).not.toBeInTheDocument();
    expect(within(screen.getByRole('banner')).queryByRole('link', {name: /futbot/i})).not.toBeInTheDocument();

    fireEvent.click(nav.getByRole('link', {name: 'Registrarse'}));
    expect(await screen.findByRole('heading', {name: 'Registro Usuario'})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/registro$/);
});

it('lets an anonymous club verify its email after registering', async () => {
    const email = 'nuevo-club@example.com';
    const fetchMock = renderRoute('/registro', {
        '/api/auth/register': () => jsonResponse({message: 'Código enviado'}, 202),
        '/api/auth/verify-email': () => jsonResponse({id: 1, email, clubId: 8}),
    }, () => jsonResponse(invalidSession, 401));

    await screen.findByRole('link', {name: 'Registrarse'});
    fireEvent.change(screen.getByLabelText('Nombre del Club'), {target: {value: 'Nuevo club'}});
    fireEvent.change(screen.getByLabelText('Email'), {target: {value: email}});
    fireEvent.change(screen.getByPlaceholderText('Contraseña'), {target: {value: 'contraseña-de-prueba'}});
    fireEvent.change(screen.getByPlaceholderText('Confimar-contraseña'), {target: {value: 'contraseña-de-prueba'}});
    fireEvent.click(screen.getByRole('button', {name: 'Registrar Club'}));

    expect(await screen.findByText(email)).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/verificar-email$/);
    fireEvent.change(screen.getByPlaceholderText('Ingrese el código'), {target: {value: '123456'}});
    fireEvent.click(screen.getByRole('button', {name: 'Verificar correo'}));

    expect(await screen.findByRole('link', {name: 'Ir a iniciar sesión'})).toHaveAttribute('href', '/login');
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/verify-email', expect.objectContaining({method: 'POST'}));
});

it('updates the navigation on login and logout', async () => {
    let signedIn = false;
    const fetchMock = renderRoute('/', {
        '/api/auth/login': () => {
            signedIn = true;
            return jsonResponse({id: 1, email: 'club@example.com', clubId: club.id});
        },
        '/api/auth/logout': () => {
            signedIn = false;
            return jsonResponse(null, 204);
        },
        '/api/leagues': () => jsonResponse({items: []}),
        '/api/friendly-matches?creatorName=&page=1&pageSize=20': () => jsonResponse({items: [], total: 0, page: 1, pageSize: 20}),
    }, () => signedIn ? jsonResponse(club) : jsonResponse(invalidSession, 401));

    await screen.findByRole('link', {name: 'Iniciar sesión'});
    fireEvent.change(screen.getByLabelText('Email'), {target: {value: 'club@example.com'}});
    fireEvent.change(screen.getByLabelText('Contraseña'), {target: {value: 'contraseña-de-prueba'}});
    fireEvent.click(screen.getByRole('button', {name: /iniciar sesión/i}));

    expect(await screen.findByRole('img', {name: `Escudo de ${club.name}`})).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/home$/));
    expect(screen.getByText(club.name)).toBeInTheDocument();
    expect(within(screen.getByRole('banner')).queryByRole('link', {name: /futbot/i})).not.toBeInTheDocument();
    const nav = within(screen.getByRole('navigation'));
    expect(nav.getByRole('link', {name: 'Inicio'})).toHaveAttribute('href', '/home');
    expect(nav.getByRole('link', {name: 'Mi club'})).toHaveAttribute('href', '/mi-club');
    expect(nav.getByRole('link', {name: 'Amistosos'})).toHaveAttribute('href', '/partidos-disponibles');
    expect(nav.getByRole('link', {name: 'Ligas'})).toHaveAttribute('href', '/ligas-disponibles');
    expect(nav.getByRole('link', {name: 'Clubes'})).toHaveAttribute('href', '/clubes');
    expect(nav.queryByRole('link', {name: 'Registrarse'})).not.toBeInTheDocument();
    fireEvent.click(nav.getByRole('button', {name: 'Cerrar sesión'}));

    expect(await screen.findByRole('heading', {name: /inicio de sesión/i})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/$/);
    expect(screen.getByRole('link', {name: 'Registrarse'})).toBeInTheDocument();
    expect(screen.queryByText(club.name)).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/logout', expect.objectContaining({method: 'POST'}));
});

it('redirects to / when a private request reports an expired session', async () => {
    const fetchMock = renderRoute('/ligas-disponibles', {
        '/api/leagues': () => jsonResponse(invalidSession, 401),
    });

    expect(await screen.findByRole('heading', {name: /inicio de sesión/i})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/$/);
    expect(screen.queryByRole('button', {name: 'Cerrar sesión'})).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/leagues', expect.anything());
});

it('opens the available leagues route and filters through the authenticated API', async () => {
    const leagues = {
        items: [{
            id: 42, name: 'Liga integrada', registeredCount: 1, maxTeams: 8,
            availableSlots: 7, isMember: true, status: 'open',
        }],
    };
    const fetchMock = renderRoute('/ligas-disponibles', {
        '/api/leagues': () => jsonResponse(leagues),
        '/api/leagues?name=Liga+integrada': () => jsonResponse(leagues),
    });
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument();
    expect(screen.getByText('Tu club ya está inscripto.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/leagues', expect.objectContaining({credentials: 'same-origin'}));

    fireEvent.change(screen.getByLabelText('Buscar por nombre'), {
        target: {value: '  Liga integrada  '},
    });
    fireEvent.submit(screen.getByLabelText('Buscar por nombre').closest('form'));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/leagues?name=Liga+integrada', expect.anything()));
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument();
});

it('retains the private league creation route and its request contract', async () => {
    const fetchMock = renderRoute('/crear-liga-privada', {
        '/api/leagues/private': () => jsonResponse({leagueId: 42, message: 'Liga creada exitosamente.'}, 201),
        '/api/leagues/42/lobby': () => jsonResponse({
            name: 'Liga privada integrada', status: 'open', isPrivate: true,
            minTeams: 3, maxTeams: 8, registeredTeams: 1, remainingSlots: 7,
            creatorClubId: club.id, isRegistered: true, clubs: [club],
        }),
        '/api/auth/me': () => jsonResponse({clubId: club.id}),
    });
    await screen.findByLabelText('Nombre de la liga');
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
    expect(await screen.findByRole('heading', {name: /Liga privada integrada/})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/leagues\/42\/lobby$/);
    const [, options] = fetchMock.mock.calls.find(([url]) => url === '/api/leagues/private');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
        name: 'Liga privada integrada', password: 'clave-de-liga',
        min_teams: 3, max_teams: 8,
        start_date: new Date('2030-01-01T12:00').toISOString(),
        round_interval: 'CONTINUOUS',
    });
});

it('displays the creator registration and opens the lineup from the league lobby', async () => {
    const fetchMock = renderRoute('/leagues/42/lobby', {
        '/api/leagues/42/lobby': () => jsonResponse({
            name: 'Liga integrada', status: 'open',
            isPrivate: true, minTeams: 3, maxTeams: 8, remainingSlots: 7,
            registeredTeams: 1, isRegistered: true,
            creatorClub: {id: 7, name: 'Club creador'},
            clubs: [{id: 7, name: 'Club creador'}],
        }),
        '/api/auth/me': () => jsonResponse({clubId: club.id}),
        '/api/leagues/42/lineup': () => jsonResponse({
            leagueId: 42, leagueName: 'Liga integrada', clubId: club.id,
            editable: true, version: 0, lineUp: null,
        }),
        '/api/players?page=1&limit=100': () => jsonResponse({items: [], totalPages: 1}),
        '/api/behaviours?kind=PLAYER': () => jsonResponse({items: []}),
        '/api/catalogs/formations': () => jsonResponse({items: []}),
    });
    expect(await screen.findByText('Club creador')).toBeInTheDocument();
    expect(screen.getByText('Privada')).toBeInTheDocument();
    expect(screen.getByText('Creador')).toBeInTheDocument();
    expect(screen.getByText('Tu club está inscripto.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/leagues/42/lobby', expect.anything());

    fireEvent.click(screen.getByRole('link', {name: 'Ver plantel'}));
    expect(await screen.findByRole('heading', {name: 'Plantel de Liga integrada'})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/leagues\/42\/lineup$/);
});

it('shows the cancellation page when an authenticated club opens a deleted league lobby', async () => {
    renderRoute('/leagues/42/lobby', {
        '/api/leagues/42/lobby': () => jsonResponse({detail: 'La liga no existe.'}, 404),
        '/api/auth/me': () => jsonResponse({clubId: club.id}),
    });

    expect(await screen.findByRole('heading', {name: /fue cancelada/i})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/liga-cancelada$/);
    expect(screen.getByRole('link', {name: 'Ver ligas disponibles'})).toHaveAttribute('href', '/ligas-disponibles');
});

it.each([false, true])('joins a league from the listing and opens its lobby (private: %s)', async (isPrivate) => {
    let joined = false;
    const ids = [56, 51, 55, 52, 54, 53];
    const slots = ids.map(playerId => ({playerId, behaviourId: 7}));
    const lineUp = {formationId: 2, starters: slots.slice(0, 3), substitutes: slots.slice(3)};
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
        if (url === '/api/club/me') response = club;
        else if (url === '/api/leagues') response = {items: [league]};
        else if (url === '/api/auth/me') response = {clubId: 8};
        else if (url === '/api/team/default') response = {clubId: 8, lineUp};
        else if (url.startsWith('/api/players/by-ids?')) response = players;
        else if (url === '/api/catalogs/formations') response = {items: [{
            id: 2, name: 'Equilibrada', slots: ['Arquero', 'Defensor', 'Delantero'].map(label => ({label})),
        }]};
        else if (url === '/api/behaviours') response = {items: [{
            id: 7, name: 'Ofensivo', kind: 'PLAYER', validationStatus: 'VALID',
        }]};
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
        clubId: 8, lineUp, ...(isPrivate ? {accessCode: 'clave-de-liga'} : {}),
    });
});
