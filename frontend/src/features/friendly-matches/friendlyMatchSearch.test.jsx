import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen} from '@testing-library/react';
import {MemoryRouter, Route, Routes, useLocation} from 'react-router';
import MatchesPage from './Matches.jsx';
import MatchPage from './MatchPage.jsx';
import AvailableFriendlyMatches from '../home-page/components/AvailableFriendlyMatches.jsx';
import {SessionProvider} from '../session/SessionProvider.jsx';

vi.mock('./hooks/useMatchConnection.js', () => ({useMatchConnection: () => ({
    snapshot: null, connectionStatus: 'connected', error: '', retry: vi.fn(),
})}));

const match = {matchId: 42, creatorClubName: 'River Norte', startDateTime: '2030-01-01T12:00:00Z'};
const reply = (data, status = 200) => ({ok: status < 400, status, json: async () => data});
const result = (items = [match], page = 1, total = 41) => ({items, total, page, pageSize: 20});
const pages = ['/partidos-disponibles', '/home'];
let fetchMock;
let available;
let join;
let own;

beforeEach(() => {
    vi.useFakeTimers();
    own = [];
    available = vi.fn(query => reply(result([match], Number(query.get('page')))));
    join = vi.fn(() => reply({matchId: 42}));
    fetchMock = vi.fn(async (url, options) => {
        if (url === '/api/friendly-matches/me') return reply(own);
        if (url === '/api/friendly-matches/join') return join(options);
        if (url.startsWith('/api/friendly-matches?')) return available(new URL(url, 'http://localhost').searchParams, options);
        if (url === '/api/club/me') return reply({id: 1});
        if (url === '/api/behaviours') return reply({items: []});
        throw new Error(`Solicitud inesperada: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

function Location() {
    const location = useLocation();
    return <output data-testid="url">{location.pathname + location.search}</output>;
}

async function show(path = '/partidos-disponibles') {
    await act(async () => render(<MemoryRouter initialEntries={[path]}>
        <Routes>
            <Route path="/partidos-disponibles" element={<MatchesPage/>}/>
            <Route path="/partidos/:matchId" element={<SessionProvider><MatchPage/></SessionProvider>}/>
            <Route path="/home" element={<AvailableFriendlyMatches/>}/>
        </Routes>
        <Location/>
    </MemoryRouter>));
}

async function type(name) {
    await act(async () => fireEvent.change(screen.getByLabelText('Buscar por nombre del club'), {target: {value: name}}));
}

async function tick(milliseconds = 300) {
    await act(async () => vi.advanceTimersByTime(milliseconds));
}

async function click(name) {
    await act(async () => fireEvent.click(screen.getByRole('button', {name})));
}

it.each(pages)('espera 300 ms y vuelve a la primera página al cambiar el nombre en %s', async path => {
    await show(`${path}?creatorName=River&page=2`);
    expect(available.mock.calls[0][0].get('page')).toBe('2');
    await type('Ri');
    await tick(200);
    await type('River Sur');
    await tick(299);
    expect(available).toHaveBeenCalledTimes(1);
    await tick(1);
    expect(available).toHaveBeenCalledTimes(2);
    const query = available.mock.calls[1][0];
    expect(query.get('creatorName')).toBe('River Sur');
    expect(query.get('page')).toBe('1');
    expect(query.get('pageSize')).toBe('20');
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/friendly-matches/me')).toHaveLength(path === '/home' ? 0 : 1);
});

it.each(pages)('cambia de página conservando el filtro en %s', async path => {
    await show(`${path}?creatorName=River`);
    expect(screen.getByRole('button', {name: 'Anterior'})).toBeDisabled();
    await click('Siguiente');
    expect(screen.getByText('Página 2 · 41 amistosos')).toBeInTheDocument();
    expect(available.mock.calls.at(-1)[0].get('creatorName')).toBe('River');
    await click('Anterior');
    expect(available.mock.calls.at(-1)[0].get('page')).toBe('1');
});

it.each(pages)('distingue la búsqueda sin coincidencias y permite limpiar en %s', async path => {
    available.mockImplementation(query => reply(query.get('creatorName') ? result([], 1, 0) : result()));
    await show(path);
    await type('Sin rival');
    await tick();
    expect(screen.getByText('No se encontraron amistosos para "Sin rival".')).toBeInTheDocument();
    await click('Limpiar');
    await tick();
    expect(screen.getByLabelText('Buscar por nombre del club')).toHaveValue('');
    expect(available.mock.calls.at(-1)[0].get('creatorName')).toBe('');
    expect(screen.getByText('River Norte')).toBeInTheDocument();
});

it.each(pages.flatMap(path => [200, 500].map(status => [path, status])))(
    'descarta una respuesta anterior tardía en %s con estado %s', async (path, status) => {
    let complete;
    available.mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
    await show(path);
    const signal = available.mock.calls[0][1].signal;
    await type('River');
    expect(signal.aborted).toBe(true);
    await tick();
    expect(screen.getByText('River Norte')).toBeInTheDocument();
    await act(async () => complete(reply(status === 200 ? result([{...match, creatorClubName: 'Resultado viejo'}])
        : {error: {message: 'Error viejo'}}, status)));
    expect(screen.queryByText('Resultado viejo')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('River Norte')).toBeInTheDocument();
});

it.each(pages)('permite repetir la misma búsqueda después de un error de red en %s', async path => {
    available.mockRejectedValueOnce(new TypeError('network'));
    await show(`${path}?creatorName=River`);
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo conectar');
    await click('Reintentar búsqueda');
    expect(screen.getByText('River Norte')).toBeInTheDocument();
    expect(available).toHaveBeenCalledTimes(2);
});

it.each(pages)('normaliza espacios sin dejar la búsqueda cargando en %s', async path => {
    await show(`${path}?creatorName=River`);
    await type(' River ');
    await tick();
    expect(screen.queryByText('Buscando amistosos…')).not.toBeInTheDocument();
    expect(screen.getByText('River Norte')).toBeInTheDocument();
    expect(available.mock.calls.at(-1)[0].get('creatorName')).toBe('River');
});

it('informa un conflicto al unirse y vuelve a consultar la misma página y filtro', async () => {
    let taken = false;
    available.mockImplementation(query => reply(result(taken ? [] : [match], Number(query.get('page')), taken ? 0 : 41)));
    join.mockImplementation(() => {
        taken = true;
        return reply({error: {code: 'MATCH_FULL', message: 'El partido ya tiene visitante.'}}, 409);
    });
    await show('/partidos-disponibles?creatorName=River&page=2');
    await click('Unirse');
    expect(screen.getByRole('alert')).toHaveTextContent('El partido ya tiene visitante.');
    expect(screen.queryByRole('button', {name: 'Unirse'})).not.toBeInTheDocument();
    const query = available.mock.calls.at(-1)[0];
    expect(query.get('creatorName')).toBe('River');
    expect(query.get('page')).toBe('2');
    expect(available).toHaveBeenCalledTimes(2);
    expect(JSON.parse(join.mock.calls[0][0].body)).toEqual({idPartido: 42});
});

it.each(['join', 'view'])('recupera el filtro y la página al volver del partido; acceso=%s', async access => {
    if (access === 'view') own = [{...match, visitorClubName: 'Mi club', status: 'SCHEDULED', isCreator: false}];
    const path = '/partidos-disponibles?creatorName=River&page=2';
    await show(path);
    if (access === 'join') await click('Unirse');
    else await act(async () => fireEvent.click(screen.getByRole('link', {name: 'Ver partido 42'})));
    const back = screen.getByRole('link', {name: 'Volver a amistosos'});
    expect(back).toHaveAttribute('href', path);
    await act(async () => fireEvent.click(back));
    expect(screen.getByTestId('url')).toHaveTextContent(path);
    expect(screen.getByLabelText('Buscar por nombre del club')).toHaveValue('River');
    expect(screen.getByText('Página 2 · 41 amistosos')).toBeInTheDocument();
});

it('conserva el contexto desde la portada al listado y al volver del partido', async () => {
    const query = '?creatorName=River&page=2';
    await show(`/home${query}`);
    const listing = screen.getByRole('link', {name: 'Ver mis amistosos y los disponibles'});
    expect(listing).toHaveAttribute('href', `/partidos-disponibles${query}`);
    await act(async () => fireEvent.click(listing));
    expect(screen.getByLabelText('Buscar por nombre del club')).toHaveValue('River');
    expect(screen.getByText('Página 2 · 41 amistosos')).toBeInTheDocument();
    await click('Unirse');
    await act(async () => fireEvent.click(screen.getByRole('link', {name: 'Volver a amistosos'})));
    expect(screen.getByTestId('url')).toHaveTextContent(`/partidos-disponibles${query}`);
    expect(screen.getByLabelText('Buscar por nombre del club')).toHaveValue('River');
    expect(screen.getByText('Página 2 · 41 amistosos')).toBeInTheDocument();
});
