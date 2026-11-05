import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import InscripcionLigaPage from './InscripcionLigaPage.jsx';

let league;
let saved;
let players;
let join;
let fetchMock;

function response(data, status = 200, headers = {}) {
    return {ok: status < 400, status, headers: new Headers(headers), json: async () => data};
}

beforeEach(() => {
    league = {id: 42, name: 'Liga privada', isPrivate: true, isRegistered: false};
    const selections = [8, 2, 7, 6, 1, 5].map(playerId => ({playerId, behaviourId: 20}));
    saved = {clubId: 9, lineUp: {formationId: 2, starters: selections.slice(0, 3), substitutes: selections.slice(3)}};
    players = [1, 2, 3, 4, 5, 6, 7, 8].map(id => ({id, name: `Jugador ${id}`}));
    join = vi.fn(async () => response({message: 'Inscripto'}, 201));
    fetchMock = vi.fn(async (url, options) => {
        if (url.endsWith('/join')) return join(url, options);
        if (url.endsWith('/lobby')) return response(league);
        if (url === '/api/team/default') {
            return saved ? response(saved) : response({error: {code: 'ACCOUNT_INCOMPLETE'}}, 409);
        }
        if (url.startsWith('/api/players/by-ids?')) return response(players);
        throw new Error(`Petición inesperada: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
});

async function openPage() {
    render(<MemoryRouter initialEntries={[`/leagues/${league.id}/join`]}>
        <Routes>
            <Route path="/leagues/:id/join" element={<InscripcionLigaPage/>}/>
            <Route path="/leagues/:id/lobby" element={<p>Inscripción confirmada por el servidor</p>}/>
        </Routes>
    </MemoryRouter>);
    return screen.findByRole('button', {name: 'Confirmar inscripción'});
}

it.each([true, false])('envía el equipo guardado a la liga elegida (privada %s)', async isPrivate => {
    league.isPrivate = isPrivate;
    league.id = 84;
    const button = await openPage();
    expect(screen.getAllByRole('listitem').map(item => item.textContent)).toEqual(
        [8, 2, 7, 6, 1, 5].map(id => `Jugador ${id}`),
    );
    if (isPrivate) {
        expect(button).toBeDisabled();
        fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: 'clave-elegida'}});
    } else {
        expect(screen.queryByLabelText('Código de acceso')).not.toBeInTheDocument();
    }
    fireEvent.click(button);
    expect(await screen.findByText('Inscripción confirmada por el servidor')).toBeInTheDocument();
    const [url, options] = join.mock.calls[0];
    expect(url).toBe('/api/leagues/84/join');
    expect(JSON.parse(options.body)).toEqual({
        clubId: 9, lineUp: [8, 2, 7, 6, 1, 5], ...(isPrivate ? {accessCode: 'clave-elegida'} : {}),
    });
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/players')).toBe(false);
    expect(fetchMock.mock.calls.find(([url]) => url.startsWith('/api/players/by-ids?'))[0])
        .toBe('/api/players/by-ids?ids=8&ids=2&ids=7&ids=6&ids=1&ids=5');
});

it.each(['missing', 'incomplete', 'duplicate', 'unavailable'])('bloquea un equipo %s y permite configurarlo', async invalid => {
    if (invalid === 'missing') saved = null;
    else if (invalid === 'incomplete') saved.lineUp.starters.pop();
    else if (invalid === 'duplicate') saved.lineUp.starters[0] = saved.lineUp.substitutes[0];
    else players = players.filter(player => player.id !== 8);
    render(<MemoryRouter><InscripcionLigaPage league={league}/></MemoryRouter>);
    expect(await screen.findByRole('link', {name: 'Configurar mi equipo'})).toHaveAttribute('href', '/mi-club');
    expect(screen.queryByRole('button', {name: 'Confirmar inscripción'})).not.toBeInTheDocument();
    expect(join).not.toHaveBeenCalled();
});

it('impide enviar una contraseña vacía y evita doble clic mientras espera el servidor', async () => {
    let finish;
    join.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const button = await openPage();
    fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: '   '}});
    expect(button).toBeDisabled();
    expect(join).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: 'clave'}});
    fireEvent.click(button);
    fireEvent.click(button);
    expect(join).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', {name: 'Inscribiendo...'})).toBeDisabled();
    expect(screen.queryByText('Inscripción confirmada por el servidor')).not.toBeInTheDocument();
    await act(async () => finish(response({message: 'Inscripto'}, 201)));
    expect(await screen.findByText('Inscripción confirmada por el servidor')).toBeInTheDocument();
});

it('muestra el error junto a la contraseña, conserva el equipo y permite corregirla', async () => {
    join.mockResolvedValueOnce(response({error: {code: 'LEAGUE_ACCESS_INVALID', message: 'clave-secreta'}}, 409));
    const button = await openPage();
    const input = screen.getByLabelText('Código de acceso');
    fireEvent.change(input, {target: {value: 'clave-secreta'}});
    fireEvent.click(button);
    expect(await screen.findByRole('alert')).toHaveTextContent('La contraseña de la liga es incorrecta.');
    expect(input).toHaveAccessibleDescription('La contraseña de la liga es incorrecta. Revisala y volvé a intentar.');
    expect(input).toHaveValue('clave-secreta');
    expect(screen.getByRole('alert')).not.toHaveTextContent('clave-secreta');
    expect(screen.getAllByRole('listitem')).toHaveLength(6);
    fireEvent.change(input, {target: {value: 'corregida'}});
    expect(input).toHaveAttribute('aria-invalid', 'false');
    fireEvent.click(button);
    expect(await screen.findByText('Inscripción confirmada por el servidor')).toBeInTheDocument();
});

it.each([
    ['LEAGUE_FULL', 'La liga está completa. No quedan cupos disponibles.'],
    ['LEAGUE_CLOSED', 'Las inscripciones de esta liga están cerradas.'],
    ['ALREADY_REGISTERED', 'Tu club ya está inscripto en esta liga.'],
])('distingue %s por su código', async (code, message) => {
    join.mockResolvedValue(response({error: {code, message: 'Mensaje sin relación con el código'}}, 409));
    const button = await openPage();
    fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: 'clave'}});
    fireEvent.click(button);
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.getByLabelText('Código de acceso')).toHaveAttribute('aria-invalid', 'false');
    expect(screen.queryByText('Inscripción confirmada por el servidor')).not.toBeInTheDocument();
});

it.each(['header', 'body'])('respeta la espera recibida en el %s de un 429', async source => {
    const fields = source === 'body' ? {retryAfter: '3'} : {};
    const headers = source === 'header' ? {'Retry-After': '3'} : {};
    join.mockResolvedValueOnce(response({error: {code: 'LEAGUE_ACCESS_RATE_LIMIT', fields}}, 429, headers));
    const button = await openPage();
    fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: 'clave'}});
    vi.useFakeTimers();
    await act(async () => fireEvent.click(button));
    expect(screen.getByRole('alert')).toHaveTextContent('3 segundos');
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(join).toHaveBeenCalledTimes(1);
    for (let second = 0; second < 3; second++) {
        await act(async () => vi.advanceTimersByTimeAsync(1000));
    }
    expect(button).toBeEnabled();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await act(async () => fireEvent.click(button));
    expect(join).toHaveBeenCalledTimes(2);
    expect(screen.getByText('Inscripción confirmada por el servidor')).toBeInTheDocument();
});

it('un fallo de red conserva el formulario y permite reintentar', async () => {
    join.mockRejectedValueOnce(new Error('Sin conexión'));
    const button = await openPage();
    fireEvent.change(screen.getByLabelText('Código de acceso'), {target: {value: 'clave'}});
    fireEvent.click(button);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor.');
    expect(screen.getByLabelText('Código de acceso')).toHaveValue('clave');
    fireEvent.click(button);
    expect(await screen.findByText('Inscripción confirmada por el servidor')).toBeInTheDocument();
});
