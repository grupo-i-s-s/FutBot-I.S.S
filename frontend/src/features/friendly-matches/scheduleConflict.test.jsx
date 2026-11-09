import {act, cleanup, fireEvent, render, screen, within} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import {toast} from 'sonner';
import {afterEach, expect, it, vi} from 'vitest';
import App from '../../App.jsx';
import MatchPage from './MatchPage.jsx';
import MatchesPage from './Matches.jsx';
import {SessionProvider} from '../session/SessionProvider.jsx';

vi.mock('./components/MatchCanvas.jsx', () => ({default: () => null}));

const conflictCode = 'LEAGUE_SCHEDULE_CONFLICT';
const conflictStart = new Date(2040, 5, 12, 20, 0).toISOString();
const conflictEnd = new Date(2040, 5, 12, 20, 6).toISOString();
const leagueConflict = {
    code: conflictCode,
    message: 'Tu club tiene un partido de liga en esa franja.',
    fields: {conflictStart, conflictEnd},
};

function jsonResponse(body, status = 200) {
    return {ok: status < 400, status, json: async () => body};
}

function renderCreateApp(createMatch, entry = '/crear-partido') {
    vi.stubGlobal('fetch', async (url, options) => {
        if (url === '/api/clubs/me') return jsonResponse({id: 1, name: 'Club local'});
        if (url === '/api/behaviours') return jsonResponse({items: []});
        if (url === '/api/friendly-matches' && options.method === 'POST') return createMatch(url, options);
        if (url.startsWith('/api/friendly-matches?')) return jsonResponse({items: [], total: 0, page: 2, pageSize: 20});
        if (url === '/api/matches/42') return new Promise(() => {});
        throw new Error(`Unexpected request: ${url}`);
    });
    render(<MemoryRouter initialEntries={[entry]}><App/></MemoryRouter>);
}

function notifications() {
    return within(screen.getByRole('region', {name: /^Notificaciones/}));
}

afterEach(() => {
    cleanup();
    toast.dismiss();
    vi.unstubAllGlobals();
});

it('muestra la franja ocupada en hora local al crear un amistoso', async () => {
    renderCreateApp(() => jsonResponse({error: leagueConflict}, 409));

    const input = await screen.findByLabelText('Fecha y hora de inicio');
    fireEvent.change(input, {target: {value: '2040-06-12T20:00'}});
    fireEvent.click(screen.getByRole('button', {name: 'Crear amistoso'}));

    expect(await screen.findByRole('alert')).toHaveTextContent(/franja ocupada es .*20:00.*20:06/);
    expect(input).toHaveValue('2040-06-12T20:00');
    expect(await notifications().findByText('No se pudo crear el amistoso')).toBeVisible();
    expect(notifications().getByText(/franja ocupada es .*20:00.*20:06/)).toBeVisible();
});

it('rechaza un horario pasado antes de enviar el formulario', async () => {
    const createMatch = vi.fn();
    renderCreateApp(createMatch);

    const input = await screen.findByLabelText('Fecha y hora de inicio');
    fireEvent.change(input, {target: {value: '2000-01-01T12:00'}});
    fireEvent.submit(input.form);

    expect(screen.getByRole('alert')).toHaveTextContent(/futura/);
    expect(input).toHaveValue('2000-01-01T12:00');
    expect(createMatch).not.toHaveBeenCalled();
    expect(notifications().queryByText('No se pudo crear el amistoso')).not.toBeInTheDocument();
});

const availableMatches = '/partidos-disponibles?creatorName=River&page=2#amistosos';

it.each([
    {entry: availableMatches, destination: availableMatches},
    {
        entry: {pathname: '/crear-partido', state: {returnTo: '//example.org/partidos-disponibles'}},
        destination: '/partidos-disponibles',
    },
])('crea un amistoso una sola vez y vuelve a $destination', async ({entry, destination}) => {
    const pending = Promise.withResolvers();
    const createMatch = vi.fn(() => pending.promise);
    renderCreateApp(createMatch, entry);

    if (entry === availableMatches) fireEvent.click(await screen.findByRole('link', {name: 'Crear amistoso'}));
    expect(await screen.findByRole('link', {name: 'Volver a amistosos'})).toHaveAttribute('href', destination);
    const input = screen.getByLabelText('Fecha y hora de inicio');
    fireEvent.change(input, {target: {value: '2040-06-12T20:00'}});
    fireEvent.click(screen.getByRole('button', {name: 'Crear amistoso'}));
    fireEvent.submit(input.form);

    expect(createMatch).toHaveBeenCalledExactlyOnceWith('/api/friendly-matches', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({startDateTime: conflictStart}),
    }));
    expect(screen.getByRole('button', {name: /^Creando/})).toBeDisabled();

    await act(async () => pending.resolve(jsonResponse({matchId: 42}, 201)));
    expect(await screen.findByRole('heading', {name: 'El partido'})).toBeVisible();
    expect(screen.getByRole('link', {name: 'Volver a amistosos'})).toHaveAttribute('href', destination);
    expect(await notifications().findByText('Amistoso creado')).toBeVisible();
});

it.each([leagueConflict, {
    code: 'FRIENDLY_SCHEDULE_CONFLICT',
    message: 'El club rival ya tiene un amistoso confirmado en ese horario. Elegí otro horario.',
    fields: {conflictStart, conflictEnd},
}])('muestra la franja ocupada al unirse a un amistoso ($code)', async error => {
    vi.stubGlobal('fetch', vi.fn(async (url) => {
        if (url === '/api/friendly-matches/42/join') return jsonResponse({error}, 409);
        return jsonResponse({
            items: [{matchId: 42, creatorClubName: 'Club local', startDateTime: conflictStart}],
            total: 1, page: 1, pageSize: 20,
        });
    }));
    render(<MemoryRouter><MatchesPage/></MemoryRouter>);

    fireEvent.click(await screen.findByRole('button', {name: 'Unirse'}));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(error.message);
    expect(alert).toHaveTextContent(/franja ocupada es .*20:00.*20:06/);
    expect(await screen.findByRole('button', {name: 'Unirse'})).toBeEnabled();
});

it.each([
    [conflictCode, 0, /se superpone con una ronda de liga confirmada/],
    ['CHECKPOINT_UNRECOVERABLE', 2, /no se pudo recuperar el estado guardado.*partido quedó sin resultado/],
])('explica en el detalle la cancelación por %s', async (reason, localScore, message) => {
    vi.stubGlobal('fetch', vi.fn(async (url) => {
        if (url === '/api/clubs/me') return jsonResponse({id: 1});
        if (url === '/api/behaviours') return jsonResponse({items: []});
        return jsonResponse({
            schemaVersion: 1, type: 'match.snapshot', matchId: 42, sequence: 1, sentAt: conflictStart,
            state: {
                status: 'CANCELLED', cancellationReason: reason, clockMs: 0, durationMs: 300_000,
                field: {width: 1000, height: 600, goalWidth: 120},
                teams: [
                    {id: 1, name: 'Club local', side: 'LEFT', score: localScore},
                    {id: 2, name: 'Club visitante', side: 'RIGHT', score: 0},
                ],
                players: [], ball: null,
            },
        });
    }));
    render(<MemoryRouter initialEntries={['/partidos/42']}>
        <SessionProvider>
            <Routes><Route path="/partidos/:matchId" element={<MatchPage/>}/></Routes>
        </SessionProvider>
    </MemoryRouter>);

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Cancelado');
    expect(screen.getByLabelText(`Marcador: ${localScore} a 0`)).toBeInTheDocument();
    expect(screen.queryByText(/Ganó|terminó en empate/)).not.toBeInTheDocument();
});
