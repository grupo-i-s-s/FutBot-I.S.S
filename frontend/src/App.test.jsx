import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {createMemoryRouter, RouterProvider, useLocation} from 'react-router';
import {toast} from 'sonner';
import App from './App.jsx';

vi.mock('./features/friendly-matches/hooks/useMatchConnection.js', () => ({
    useMatchConnection: () => ({snapshot: null, connectionStatus: 'loading', error: ''}),
}));

const club = {id: 8, name: 'Club de pruebas', avatar: 'avatar-01.png', friendlyAvailable: true};
const invalidSession = {error: {code: 'SESSION_INVALID', message: 'La sesión venció.'}};
const emptyList = () => jsonResponse({items: []});
const myClubResponses = {
    '/api/behaviours': emptyList,
    '/api/clubs/me/leagues': emptyList,
    '/api/clubs/me/dt/behaviours': emptyList,
    '/api/players?page=1&pageSize=9': () => jsonResponse({items: [], total: 0, totalPages: 1}),
    '/api/clubs/me/default-team': () => jsonResponse(null),
    '/api/catalogs/formations': emptyList,
};

afterEach(() => {
    cleanup();
    toast.dismiss();
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
    const {pathname, search, hash, state} = useLocation();
    return (
        <span hidden data-testid="current-path" data-search={search} data-hash={hash}
              data-navigation-state={JSON.stringify(state)}>{pathname}</span>
    );
}

function renderApp(path) {
    const router = createMemoryRouter([{path: '*', element: <><App/><CurrentPath/></>}], {
        initialEntries: [path],
    });
    render(<RouterProvider router={router}/>);
}

function renderRoute(path, responses = {}, getClub = () => jsonResponse(club)) {
    const fetchMock = vi.fn(async (url, options) => {
        if (url === '/api/clubs/me') return getClub();
        const respond = responses[url];
        if (!respond) throw new Error(`Unexpected request: ${url}`);
        return respond(options);
    });
    vi.stubGlobal('fetch', fetchMock);
    renderApp(path);
    return fetchMock;
}

it.each([
    '/ligas-disponibles', '/liga-cancelada', '/clubes', '/clubes/42',
    '/comportamientos', '/crear-comportamiento-dt', '/ligas/42/plantel', '/leagues/42/lineup', '/ranking-global',
])('redirects anonymous visits to %s to /', async (path) => {
    const fetchMock = renderRoute(path, {}, () => jsonResponse(invalidSession, 401));

    expect(await screen.findByRole('heading', {name: /inicio de sesión/i})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/$/);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/api/clubs/me']);
    const nav = within(screen.getByRole('navigation'));
    expect(nav.getByRole('link', {name: 'Iniciar sesión'})).toBeInTheDocument();
    expect(nav.getByRole('link', {name: 'Registrarse'})).toHaveAttribute('href', '/registro');
    expect(nav.queryByRole('link', {name: 'Mi club'})).not.toBeInTheDocument();
    expect(within(screen.getByRole('banner')).queryByRole('link', {name: /futbot/i})).not.toBeInTheDocument();

    fireEvent.click(nav.getByRole('link', {name: 'Registrarse'}));
    expect(await screen.findByRole('heading', {name: 'Registrá tu club'})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/registro$/);
});

it.each([
    '/comportamientos', '/comportamientos/42', '/crear-comportamiento', '/behaviours', '/behaviours/42',
])('redirects %s to the club catalogue without opening a page or dialog', async (path) => {
    const fetchMock = renderRoute(path, myClubResponses);

    expect(await screen.findByRole('tab', {name: 'Comportamientos', selected: true})).toBeVisible();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/mi-club$/);
    expect(screen.getByTestId('current-path')).toHaveAttribute('data-search', '?tab=behaviours');
    expect(screen.getByRole('button', {name: 'Crear nuevo comportamiento'})).toBeVisible();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).not.toContain('/api/behaviours/42');
});

it('retries a failed behaviour test and returns to the club catalogue from the match', async () => {
    const createTest = vi.fn()
        .mockReturnValueOnce(jsonResponse({error: {message: 'El equipo no está completo.'}}, 409))
        .mockReturnValueOnce(jsonResponse({matchId: 42}, 201));
    renderRoute('/mi-club?tab=behaviours', {
        ...myClubResponses,
        '/api/friendly-matches/behaviour-test': createTest,
    });

    const button = await screen.findByRole('button', {name: 'Probar comportamiento'});
    fireEvent.click(button);
    expect(button).toBeDisabled();
    const notifications = within(screen.getByRole('region', {name: /^Notificaciones/}));
    expect(await notifications.findByText('No se pudo iniciar la prueba')).toBeVisible();
    expect(notifications.getByText('El equipo no está completo.')).toBeVisible();
    expect(button).toBeEnabled();
    fireEvent.click(button);

    const returnLink = await screen.findByRole('link', {name: 'Volver a comportamientos'});
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/partidos\/42$/);
    expect(await notifications.findByText('Partido de prueba creado')).toBeVisible();
    expect(createTest).toHaveBeenCalledTimes(2);
    expect(createTest).toHaveBeenLastCalledWith(expect.objectContaining({method: 'POST'}));
    expect(returnLink).toHaveAttribute('href', '/mi-club?tab=behaviours');
    fireEvent.click(returnLink);
    expect(await screen.findByRole('tab', {name: 'Comportamientos', selected: true})).toBeVisible();
});

it('redirects the old login URL without losing the query, anchor or navigation state', async () => {
    const state = {returnTo: '/mi-club'};
    renderRoute({pathname: '/login', search: '?origen=registro', hash: '#sesion', state},
        {}, () => jsonResponse(invalidSession, 401));

    expect(await screen.findByRole('heading', {name: /inicio de sesión/i})).toBeInTheDocument();
    const location = screen.getByTestId('current-path');
    expect(location).toHaveTextContent(/^\/iniciar-sesion$/);
    expect(location).toHaveAttribute('data-search', '?origen=registro');
    expect(location).toHaveAttribute('data-hash', '#sesion');
    expect(location).toHaveAttribute('data-navigation-state', JSON.stringify(state));
});

it.each(['/home', '/login'])('redirects %s to the authenticated home with its filters', async (pathname) => {
    const search = '?creatorName=River&page=2';
    const hash = '#amistosos';
    const state = {returnTo: '/mi-club'};
    const fetchMock = renderRoute({pathname, search, hash, state}, {
        '/api/leagues?page=1&pageSize=100': () => jsonResponse({items: []}),
        '/api/friendly-matches?creatorName=River&page=2&pageSize=20': () => jsonResponse({
            items: [], total: 0, page: 2, pageSize: 20,
        }),
    });

    const listing = await screen.findByRole('link', {name: 'Ver amistosos disponibles'});
    expect(listing).toHaveAttribute('href', `/partidos-disponibles${search}${hash}`);
    const location = screen.getByTestId('current-path');
    expect(location).toHaveTextContent(/^\/inicio$/);
    expect(location).toHaveAttribute('data-search', search);
    expect(location).toHaveAttribute('data-hash', hash);
    expect(location).toHaveAttribute('data-navigation-state', JSON.stringify(state));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
        '/api/friendly-matches?creatorName=River&page=2&pageSize=20', expect.anything(),
    ));
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
    fireEvent.change(screen.getByLabelText('Contraseña', {exact: true}), {target: {value: 'contraseña-de-prueba'}});
    fireEvent.change(screen.getByLabelText('Confirmar contraseña', {exact: true}), {target: {value: 'contraseña-de-prueba'}});
    fireEvent.click(screen.getByRole('button', {name: 'Registrar Club'}));

    expect(await screen.findByText(email)).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/verificar-email$/);
    const notifications = within(screen.getByRole('region', {name: /^Notificaciones/}));
    expect(await notifications.findByText('Código de verificación enviado')).toBeVisible();
    fireEvent.change(screen.getByPlaceholderText('Ingrese el código'), {target: {value: '123456'}});
    fireEvent.click(screen.getByRole('button', {name: 'Verificar correo'}));

    expect(await screen.findByRole('link', {name: 'Ir a iniciar sesión'})).toHaveAttribute('href', '/iniciar-sesion');
    expect(await notifications.findByText('Correo verificado')).toBeVisible();
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
        '/api/leagues?page=1&pageSize=100': () => jsonResponse({items: []}),
        '/api/friendly-matches?creatorName=&page=1&pageSize=20': () => jsonResponse({items: [], total: 0, page: 1, pageSize: 20}),
    }, () => signedIn ? jsonResponse(club) : jsonResponse(invalidSession, 401));

    await screen.findByRole('link', {name: 'Iniciar sesión'});
    fireEvent.change(screen.getByLabelText('Email'), {target: {value: 'club@example.com'}});
    fireEvent.change(screen.getByLabelText('Contraseña'), {target: {value: 'contraseña-de-prueba'}});
    fireEvent.click(screen.getByRole('button', {name: /iniciar sesión/i}));

    expect(await screen.findByRole('img', {name: `Escudo de ${club.name}`})).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/inicio$/));
    const notifications = within(screen.getByRole('region', {name: /^Notificaciones/}));
    expect(await notifications.findByText('Sesión iniciada')).toBeVisible();
    expect(screen.getByText(club.name)).toBeInTheDocument();
    expect(within(screen.getByRole('banner')).queryByRole('link', {name: /futbot/i})).not.toBeInTheDocument();
    const nav = within(screen.getByRole('navigation'));
    expect(nav.getByRole('link', {name: 'Inicio'})).toHaveAttribute('href', '/inicio');
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
        '/api/leagues?page=1&pageSize=100': () => jsonResponse(invalidSession, 401),
    });

    expect(await screen.findByRole('heading', {name: /inicio de sesión/i})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/$/);
    expect(screen.queryByRole('button', {name: 'Cerrar sesión'})).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/leagues?page=1&pageSize=100', expect.anything());
});

it('opens the global ranking from the authenticated home', async () => {
    renderRoute('/inicio', {
        '/api/leagues?page=1&pageSize=100': () => jsonResponse({items: []}),
        '/api/friendly-matches?creatorName=&page=1&pageSize=20': () => jsonResponse({items: [], total: 0, page: 1, pageSize: 20}),
        '/api/ranking-global?page=1&pageSize=20': () => jsonResponse({
            items: [{
                id: 9, position: 1, name: 'Club líder', avatar: 'avatar-01.png',
                points: 12, played: 4, wins: 4, draws: 0, losses: 0, goalsFor: 10, goalsAgainst: 2, dg: 8,
            }],
            page: 1, pageSize: 20, total: 21, totalPages: 2, hasNext: true,
        }),
        '/api/ranking-global?page=2&pageSize=20': () => jsonResponse({
            items: [{
                id: 29, position: 21, name: 'Club siguiente', avatar: 'avatar-02.png',
                points: 0, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, dg: 0,
            }],
            page: 2, pageSize: 20, total: 21, totalPages: 2, hasNext: false,
        }),
    });

    fireEvent.click(await screen.findByRole('link', {name: 'Ranking global'}));

    expect(await screen.findByRole('heading', {name: 'Ranking Global'})).toBeInTheDocument();
    const leader = (await screen.findByRole('rowheader', {name: /club líder/i})).closest('tr');
    expect(within(leader).getByRole('img', {name: 'Escudo de Club líder'})).toBeInTheDocument();
    expect(screen.getByRole('columnheader', {name: 'GF'})).toBeInTheDocument();
    expect(screen.getByRole('columnheader', {name: 'GC'})).toBeInTheDocument();
    expect(within(leader).getByText('10')).toBeInTheDocument();
    expect(within(leader).getByText('2')).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/ranking-global$/);

    fireEvent.click(screen.getByRole('button', {name: 'Siguiente'}));

    const nextClub = (await screen.findByRole('rowheader', {name: /club siguiente/i})).closest('tr');
    expect(within(nextClub).getByText('21')).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Siguiente'})).toBeDisabled();
    expect(screen.getByRole('button', {name: 'Anterior'})).toBeEnabled();
});

it('opens the available leagues route and filters through the authenticated API', async () => {
    const leagues = {
        items: [{
            id: 42, name: 'Liga integrada', registeredCount: 1, maxTeams: 8,
            availableSlots: 7, isMember: true, status: 'open',
        }],
    };
    const fetchMock = renderRoute('/ligas-disponibles', {
        '/api/leagues?page=1&pageSize=100': () => jsonResponse(leagues),
        '/api/leagues?page=1&pageSize=100&name=Liga+integrada': () => jsonResponse({...leagues, hasNext: true}),
        '/api/leagues?page=2&pageSize=100&name=Liga+integrada': () => jsonResponse({
            items: [{...leagues.items[0], id: 43, name: 'Liga integrada B', isMember: false}],
            hasNext: false,
        }),
    });
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument();
    expect(screen.getByText('Tu club ya está inscripto.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/leagues?page=1&pageSize=100', expect.objectContaining({credentials: 'same-origin'}));

    fireEvent.change(screen.getByLabelText('Buscar por nombre'), {
        target: {value: '  Liga integrada  '},
    });
    fireEvent.submit(screen.getByLabelText('Buscar por nombre').closest('form'));
    expect(await screen.findByText('Liga integrada B')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/leagues?page=2&pageSize=100&name=Liga+integrada', expect.anything());
    expect(await screen.findByText('Liga integrada')).toBeInTheDocument();
});

it.each([
    ['/crear-liga', 'Crear liga pública'],
    ['/crear-liga-privada', 'Crear liga privada'],
])('opens %s over the home page and returns home on close', async (path, title) => {
    renderRoute(path, {
        '/api/friendly-matches?creatorName=&page=1&pageSize=20': () => jsonResponse({items: [], total: 0, page: 1, pageSize: 20}),
    });

    const dialog = await screen.findByRole('dialog', {name: title});
    expect(document.getElementById('home-title')).toHaveTextContent('Bienvenidos a');
    expect(within(dialog).getByLabelText('Nombre de la liga')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', {name: 'Cerrar'}));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/inicio$/);
    expect(screen.getByRole('heading', {name: /Bienvenidos a/})).toBeInTheDocument();
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
        ['Confirmar contraseña', 'clave-de-liga'],
        ['Máximo de clubes', '8'],
        ['Fecha y hora de inicio', '2030-01-01T12:00'],
    ]) {
        fireEvent.change(screen.getByLabelText(label), {target: {value}});
    }
    fireEvent.submit(screen.getByRole('button', {name: 'Crear liga'}).closest('form'));
    expect(await screen.findByRole('heading', {name: /Liga privada integrada/})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/ligas\/42\/sala-de-espera$/);
    const [, options] = fetchMock.mock.calls.find(([url]) => url === '/api/leagues/private');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
        name: 'Liga privada integrada', password: 'clave-de-liga',
        min_teams: 3, max_teams: 8,
        start_date: new Date('2030-01-01T12:00').toISOString(),
        round_interval: 'CONTINUOUS',
    });
});

it('redirects the old league lobby URL and opens the lineup from the Spanish lobby', async () => {
    const state = {returnTo: '/ligas-disponibles?page=2'};
    const fetchMock = renderRoute({pathname: '/leagues/42/lobby', search: '?origen=lista', hash: '#clubes', state}, {
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
        '/api/players?page=1&pageSize=100': () => jsonResponse({items: [], totalPages: 1}),
        '/api/behaviours?kind=PLAYER': () => jsonResponse({items: []}),
        '/api/catalogs/formations': () => jsonResponse({items: []}),
    });
    expect(await screen.findByText('Club creador')).toBeInTheDocument();
    expect(screen.getByText('Privada')).toBeInTheDocument();
    expect(screen.getByText('Creador')).toBeInTheDocument();
    expect(screen.getByText('Tu club está inscripto.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/leagues/42/lobby', expect.anything());
    const location = screen.getByTestId('current-path');
    expect(location).toHaveTextContent(/^\/ligas\/42\/sala-de-espera$/);
    expect(location).toHaveAttribute('data-search', '?origen=lista');
    expect(location).toHaveAttribute('data-hash', '#clubes');
    expect(location).toHaveAttribute('data-navigation-state', JSON.stringify(state));

    fireEvent.click(screen.getByRole('link', {name: 'Ver plantel'}));
    expect(await screen.findByRole('heading', {name: 'Plantel de Liga integrada'})).toBeInTheDocument();
    expect(screen.getByTestId('current-path')).toHaveTextContent(/^\/ligas\/42\/plantel$/);
});

it.each([
    '/leagues/42/join?leagueId=42&origen=lista#equipo',
    '/inscripcion-liga?leagueId=42&origen=lista#equipo',
])('redirects old registration URL %s to the league registration', async (url) => {
    renderRoute(url, {
        '/api/leagues/42/lobby': () => jsonResponse({
            id: 42, name: 'Liga integrada', isRegistered: true,
        }),
    });

    expect(await screen.findByText('Inscripción confirmada')).toBeInTheDocument();
    const location = screen.getByTestId('current-path');
    expect(location).toHaveTextContent(/^\/ligas\/42\/inscripcion$/);
    expect(location).toHaveAttribute('data-search', '?leagueId=42&origen=lista');
    expect(location).toHaveAttribute('data-hash', '#equipo');
});

it('keeps the missing-league message on the old registration URL with no league selected', async () => {
    renderRoute('/inscripcion-liga');

    expect(await screen.findByText('No se seleccionó ninguna liga')).toBeInTheDocument();
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
        if (url === '/api/clubs/me') response = club;
        else if (url === '/api/leagues?page=1&pageSize=100') response = {items: [league]};
        else if (url === '/api/auth/me') response = {clubId: 8};
        else if (url === '/api/clubs/me/default-team') response = {clubId: 8, lineUp};
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
    renderApp('/ligas-disponibles');
    fireEvent.click(await screen.findByRole('link', {name: 'Inscribirse'}));
    expect(await screen.findByText('Jugadora del club')).toBeInTheDocument();
    if (isPrivate) {
        fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: 'clave-de-liga'}});
    }
    fireEvent.click(screen.getByRole('button', {name: 'Confirmar inscripción'}));
    expect(await screen.findByText('Tu club está inscripto.')).toBeInTheDocument();
    expect(within(screen.getByRole('tabpanel', {name: 'Lobby'})).getByRole('link', {name: 'Mi club'})).toBeInTheDocument();
    const [, options] = fetchMock.mock.calls.find(([url]) => url.endsWith('/join'));
    expect(JSON.parse(options.body)).toEqual({
        clubId: 8, lineUp, ...(isPrivate ? {accessCode: 'clave-de-liga'} : {}),
    });
});
