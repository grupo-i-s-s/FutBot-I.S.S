import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import PlannedSubstitutionPanel from './PlannedSubstitutionPanel.jsx';
import MatchPage from '../MatchPage.jsx';
import {useMatchConnection} from '../hooks/useMatchConnection.js';

vi.mock('../hooks/useMatchConnection.js', () => ({useMatchConnection: vi.fn()}));
vi.mock('./MatchCanvas.jsx', () => ({default: ({snapshot}) =>
    <div data-testid="cancha">{snapshot.state.players.map(player => player.id).join(',')}</div>}));
vi.mock('./MatchBehaviourChanges.jsx', () => ({default: () => null}));

let state;
let fetchMock;
let responseSequence;
const player = (playerId, name) => ({playerId, name});
const reply = (data, status = 200) => ({ok: status < 400, status, json: async () => data});
const pending = (inPlayerId = 4, commandId = 'saved-command') =>
    ({outPlayerId: 1, inPlayerId, commandId, pauseId: '42:1', status: 'PENDING'});

beforeEach(() => {
    responseSequence = 1;
    state = {
        status: 'RUNNING', phase: 'PLAYING', nextPause: {pauseId: '42:1', number: 1}, events: [],
        clockMs: 100, durationMs: 1000,
        teams: [{id: 1, name: 'Mi club', side: 'LEFT', score: 0}, {id: 2, name: 'Rival', side: 'RIGHT', score: 0}],
        players: [1, 2, 3, 7, 8, 9].map(id => ({id, name: `Jugador ${id}`, teamId: id < 7 ? 1 : 2})),
        lineups: [
            {clubId: 1, starters: [player(1, 'Titular A'), player(2, 'Titular B'), player(3, 'Titular C')],
                substitutes: [player(4, 'Suplente A'), player(5, 'Suplente B'), player(6, 'Suplente C')],
                remainingSubstitutions: 1, pendingSubstitution: null},
            {clubId: 2, starters: [player(7, 'Rival titular'), player(8, 'Rival B'), player(9, 'Rival C')],
                substitutes: [player(10, 'Rival suplente'), player(11, 'Banco B'), player(12, 'Banco C')],
                remainingSubstitutions: 1, pendingSubstitution: null},
        ],
    };
    fetchMock = vi.fn(async (url, options) => {
        if (url === '/api/club/me') return reply({id: 1});
        if (url === '/api/behaviours') return reply({items: []});
        expect(url).toBe('/api/matches/42/planned-substitution');
        return reply({...JSON.parse(options.body), pauseId: '42:1', status: 'PENDING', sequence: ++responseSequence});
    });
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(crypto, 'randomUUID').mockReturnValueOnce('command-1').mockReturnValueOnce('command-2').mockReturnValue('command-3');
});

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function panel(overrides = {}) {
    return <PlannedSubstitutionPanel matchId="42" state={state} sequence={1} clubId={1} connected {...overrides}/>;
}

function choose(inId = '4') {
    fireEvent.change(screen.getByLabelText('Titular que sale'), {target: {value: '1'}});
    fireEvent.change(screen.getByLabelText('Suplente que entra'), {target: {value: inId}});
}

it('ofrece únicamente los roles actuales del club y exige elegir ambos jugadores', () => {
    render(panel());
    expect(screen.getByRole('button', {name: 'Guardar cambio'})).toBeDisabled();
    expect(within(screen.getByLabelText('Titular que sale')).getAllByRole('option')).toHaveLength(4);
    expect(within(screen.getByLabelText('Suplente que entra')).getAllByRole('option')).toHaveLength(4);
    expect(screen.queryByText('Rival titular')).not.toBeInTheDocument();
    choose();
    expect(screen.getByRole('button', {name: 'Guardar cambio'})).toBeEnabled();
    expect(screen.getByText('Próxima pausa: primera hidratación.')).toBeInTheDocument();
});

it('guarda una vez, espera la respuesta y muestra planificado sin alterar la cancha', async () => {
    const before = structuredClone(state.players);
    let finish;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    render(panel());
    choose();
    const button = screen.getByRole('button', {name: 'Guardar cambio'});
    fireEvent.click(button);
    fireEvent.click(button);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', {name: 'Guardando…'})).toBeDisabled();
    expect(screen.queryByText(/Cambio planificado:/)).not.toBeInTheDocument();
    const [, options] = fetchMock.mock.calls[0];
    expect(options.method).toBe('PUT');
    expect(options.credentials).toBe('same-origin');
    expect(options.headers['X-FutBot-Request']).toBe('1');
    expect(JSON.parse(options.body)).toEqual({outPlayerId: 1, inPlayerId: 4, commandId: 'command-1'});
    await act(async () => finish(reply({...pending(4, 'command-1'), sequence: 2})));
    expect(screen.getByText(/Cambio planificado: sale Titular A y entra Suplente A/)).toHaveTextContent('todavía no se realizó');
    expect(state.players).toEqual(before);
    expect(screen.queryByText(/Cambio aplicado:/)).not.toBeInTheDocument();
});

it('reemplaza el pendiente sólo tras una respuesta exitosa y conserva el anterior ante rechazo', async () => {
    state.lineups[0].pendingSubstitution = pending();
    render(panel());
    fireEvent.change(screen.getByLabelText('Suplente que entra'), {target: {value: '5'}});
    fetchMock.mockResolvedValueOnce(reply({error: {code: 'SUBSTITUTION_INVALID_PLAYERS', message: 'Ese suplente no está disponible.'}}, 409));
    fireEvent.click(screen.getByRole('button', {name: 'Reemplazar planificación'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Ese suplente no está disponible.');
    expect(screen.getByText(/Cambio planificado:/)).toHaveTextContent('entra Suplente A');
    expect(screen.getByLabelText('Suplente que entra')).toHaveValue('5');
    fireEvent.click(screen.getByRole('button', {name: 'Reemplazar planificación'}));
    await waitFor(() => expect(screen.getByText(/Cambio planificado:/)).toHaveTextContent('entra Suplente B'));
});

it('reutiliza commandId al reintentar después de un fallo de red', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('network'));
    render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Guardar cambio'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar');
    fireEvent.click(screen.getByRole('button', {name: 'Guardar cambio'}));
    await screen.findByText(/Cambio planificado:/);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(JSON.parse(fetchMock.mock.calls[1][1].body));
});

it.each(['quota', 'no-pause', 'paused', 'disconnected'])('deshabilita el envío cuando corresponde: %s', reason => {
    if (reason === 'quota') state.lineups[0].remainingSubstitutions = 0;
    if (reason === 'no-pause') state.nextPause = null;
    if (reason === 'paused') state.phase = 'HYDRATION_BREAK';
    render(panel({connected: reason !== 'disconnected'}));
    expect(screen.getByLabelText('Titular que sale')).toBeDisabled();
    expect(screen.getByRole('button', {name: 'Guardar cambio'})).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
});

it('reconstruye la planificación desde el snapshot al volver a abrir o reconectar', () => {
    state.lineups[0].pendingSubstitution = pending();
    const view = render(panel({sequence: 10, connected: false}));
    expect(screen.getByText(/Cambio planificado:/)).toHaveTextContent('entra Suplente A');
    expect(screen.getByLabelText('Suplente que entra')).toHaveValue('4');
    view.rerender(panel({sequence: 11}));
    expect(screen.getByRole('button', {name: 'Reemplazar planificación'})).toBeEnabled();
    view.unmount();
    render(panel({sequence: 11}));
    expect(screen.getByText(/Cambio planificado:/)).toHaveTextContent('entra Suplente A');
});

it('un snapshot nuevo de otro dispositivo reemplaza una confirmación local anterior', async () => {
    const view = render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Guardar cambio'}));
    await screen.findByText(/Cambio planificado:/);
    state = {...state, lineups: [{...state.lineups[0], pendingSubstitution: pending(5, 'other-device')}, state.lineups[1]]};
    view.rerender(panel({sequence: 4}));
    expect(screen.getByText(/Cambio planificado:/)).toHaveTextContent('entra Suplente B');
});

it('una respuesta tardía no restaura un pendiente que el motor ya aplicó', async () => {
    let finish;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const view = render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Guardar cambio'}));
    state = {...state, phase: 'HYDRATION_BREAK', nextPause: {pauseId: '42:2', number: 2},
        players: state.players.map(p => p.id === 1 ? {...p, id: 4} : p),
        lineups: [{...state.lineups[0], starters: [player(4, 'Suplente A'), ...state.lineups[0].starters.slice(1)],
            substitutes: [player(1, 'Titular A'), ...state.lineups[0].substitutes.slice(1)]}, state.lineups[1]],
        events: [{eventId: 'event-1', type: 'SUBSTITUTION_APPLIED', clubId: 1, outPlayerId: 1, inPlayerId: 4}]};
    view.rerender(panel({sequence: 3}));
    await act(async () => finish(reply({...pending(), sequence: 2})));
    expect(screen.getByText(/Cambio aplicado:/)).toBeInTheDocument();
    expect(screen.queryByText(/Cambio planificado:/)).not.toBeInTheDocument();
});

it('oculta el panel a un club que no pertenece al partido', () => {
    render(panel({clubId: 99}));
    expect(screen.queryByRole('region', {name: 'Sustitución programada'})).not.toBeInTheDocument();
});

it('integra el panel en la página y cambia la cancha únicamente al recibir el snapshot aplicado', async () => {
    let snapshot = {sequence: 1, state};
    useMatchConnection.mockReturnValue({snapshot, connectionStatus: 'connected', error: '', retry: vi.fn()});
    const page = () => <MemoryRouter initialEntries={['/matches/42']}>
        <Routes><Route path="/matches/:matchId" element={<MatchPage/>}/></Routes>
    </MemoryRouter>;
    const view = render(page());
    await screen.findByRole('region', {name: 'Sustitución programada'});
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Guardar cambio'}));
    await screen.findByText(/Cambio planificado:/);
    expect(screen.getByTestId('cancha')).toHaveTextContent('1,2,3,7,8,9');
    state = {...state, players: state.players.map(p => p.id === 1 ? {...p, id: 4} : p),
        lineups: [{...state.lineups[0], starters: [player(4, 'Suplente A'), ...state.lineups[0].starters.slice(1)],
            substitutes: [player(1, 'Titular A'), ...state.lineups[0].substitutes.slice(1)]}, state.lineups[1]],
        events: [{eventId: 'applied-1', type: 'SUBSTITUTION_APPLIED', clubId: 1, outPlayerId: 1, inPlayerId: 4}]};
    snapshot = {sequence: 3, state};
    useMatchConnection.mockReturnValue({snapshot, connectionStatus: 'connected', error: '', retry: vi.fn()});
    view.rerender(page());
    expect(screen.getByTestId('cancha')).toHaveTextContent('4,2,3,7,8,9');
    expect(screen.getByText(/Cambio aplicado:/)).toBeInTheDocument();
});
