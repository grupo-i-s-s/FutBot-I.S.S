import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import {afterEach, expect, it, vi} from 'vitest';
import CreateFriendlyMatch from './Create_friendly_match.jsx';
import MatchPage from './MatchPage.jsx';
import MatchesPage from './Matches.jsx';
import {SessionProvider} from '../session/SessionProvider.jsx';

vi.mock('./components/MatchCanvas.jsx', () => ({default: () => null}));

const conflictCode = 'LEAGUE_SCHEDULE_CONFLICT';
const conflictStart = new Date(2040, 5, 12, 20, 0).toISOString();
const conflictEnd = new Date(2040, 5, 12, 20, 6).toISOString();

function jsonResponse(body, status = 200) {
    return {ok: status < 400, status, json: async () => body};
}

function conflictResponse() {
    return jsonResponse({error: {
        code: conflictCode,
        message: 'Tu club tiene un partido de liga en esa franja.',
        fields: {conflictStart, conflictEnd},
    }}, 409);
}

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

it('muestra la franja ocupada en hora local al crear un amistoso', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => conflictResponse()));
    render(<MemoryRouter><CreateFriendlyMatch/></MemoryRouter>);

    const input = screen.getByLabelText('Horario para comenzar el partido');
    fireEvent.change(input, {target: {value: '2040-06-12T20:00'}});
    fireEvent.click(screen.getByRole('button', {name: 'Crear Partido'}));

    expect(await screen.findByRole('alert')).toHaveTextContent(/franja ocupada es .*20:00.*20:06/);
    expect(input).toHaveValue('2040-06-12T20:00');
});

it('muestra la franja ocupada al intentar unirse a un amistoso', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url) => {
        if (url === '/api/friendly-matches/me') return jsonResponse([]);
        if (url === '/api/friendly-matches/join') return conflictResponse();
        return jsonResponse([{matchId: 42, creatorClubName: 'Club local', startDateTime: conflictStart}]);
    }));
    render(<MemoryRouter><MatchesPage/></MemoryRouter>);

    fireEvent.click(await screen.findByRole('button', {name: 'Unirse'}));

    expect(await screen.findByRole('alert')).toHaveTextContent(/franja ocupada es .*20:00.*20:06/);
    expect(await screen.findByRole('button', {name: 'Unirse'})).toBeEnabled();
});

it.each([
    [conflictCode, 0, /se superpone con una ronda de liga confirmada/],
    ['CHECKPOINT_UNRECOVERABLE', 2, /no se pudo recuperar el estado guardado.*partido quedó sin resultado/],
])('explica en el detalle la cancelación por %s', async (reason, localScore, message) => {
    vi.stubGlobal('fetch', vi.fn(async (url) => {
        if (url === '/api/club/me') return jsonResponse({id: 1});
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
