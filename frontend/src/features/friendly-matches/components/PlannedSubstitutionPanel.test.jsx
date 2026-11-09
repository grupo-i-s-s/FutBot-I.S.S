import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import {SessionProvider} from '../../session/SessionProvider.jsx';
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
        teams: [
            {id: 1, name: 'Mi club', side: 'LEFT', score: 0, dtActive: false},
            {id: 2, name: 'Rival', side: 'RIGHT', score: 0, dtActive: false},
        ],
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
        if (url === '/api/clubs/me') return reply({id: 1});
        if (url === '/api/behaviours') return reply({items: []});
        const manual = url === '/api/matches/42/substitutions';
        if (!manual) expect(url).toBe('/api/matches/42/planned-substitution');
        return reply({...JSON.parse(options.body), status: 'PENDING', sequence: ++responseSequence}, manual ? 202 : 200);
    });
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(crypto, 'randomUUID').mockReturnValueOnce('command-1').mockReturnValueOnce('command-2').mockReturnValue('command-3');
});

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function panel(overrides = {}) {
    return <PlannedSubstitutionPanel matchId="42" state={state} sequence={1} clubId={1}
                                     connected allowManualActions {...overrides}/>;
}

function matchPage() {
    return <MemoryRouter initialEntries={['/partidos/42']}>
        <SessionProvider>
            <Routes><Route path="/partidos/:matchId" element={<MatchPage/>}/></Routes>
        </SessionProvider>
    </MemoryRouter>;
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
    expect(JSON.parse(options.body)).toEqual({
        outPlayerId: 1, inPlayerId: 4, commandId: 'command-1', pauseId: '42:1',
    });
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

it('informa que venció la pausa elegida y espera una nueva confirmación para la siguiente', async () => {
    fetchMock.mockResolvedValueOnce(reply({error: {
        code: 'PAUSE_CLOSED', message: 'La pausa elegida ya no está disponible para planificar.',
    }}, 409));
    const view = render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Guardar cambio'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('La pausa elegida ya no está disponible');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({pauseId: '42:1', commandId: 'command-1'});
    expect(screen.queryByText(/Cambio planificado:/)).not.toBeInTheDocument();

    state = {...state, nextPause: {pauseId: '42:2', number: 2}};
    responseSequence = 3;
    view.rerender(panel({sequence: 3}));
    expect(screen.getByText('Próxima pausa: entretiempo.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', {name: 'Guardar cambio'}));
    await screen.findByText(/Se aplicará en entretiempo/);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({pauseId: '42:2', commandId: 'command-2'});
});

it.each([false, true])('un reintento vencido no vuelve a mostrar el cambio como pendiente; manual=%s', async manual => {
    if (manual) pause();
    fetchMock.mockRejectedValueOnce(new TypeError('network'));
    fetchMock.mockResolvedValueOnce(reply({...pending(4, 'command-1'), status: 'EXPIRED', sequence: 2}, manual ? 202 : 200));
    render(panel());
    choose();
    const label = manual ? 'Realizar cambio' : 'Guardar cambio';
    fireEvent.click(screen.getByRole('button', {name: label}));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar');
    fireEvent.click(screen.getByRole('button', {name: label}));
    expect(await screen.findByRole('alert')).toHaveTextContent('El cambio quedó sin efecto.');
    expect(screen.queryByText(/Cambio (planificado|pendiente):/)).not.toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual(JSON.parse(fetchMock.mock.calls[0][1].body));
});

it.each(['quota', 'no-pause', 'disconnected'])('deshabilita el envío cuando corresponde: %s', reason => {
    if (reason === 'quota') state.lineups[0].remainingSubstitutions = 0;
    if (reason === 'no-pause') state.nextPause = null;
    render(panel({connected: reason !== 'disconnected'}));
    expect(screen.getByLabelText('Titular que sale')).toBeDisabled();
    expect(screen.getByRole('button', {name: 'Guardar cambio'})).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
});

function pause(index = 1) {
    state = {...state, phase: index === 2 ? 'HALF_BREAK' : 'HYDRATION_BREAK', breakIndex: index,
        breakRemainingMs: 1000, nextPause: index === 3 ? null : {pauseId: `42:${index + 1}`, number: index + 1}};
}

function applyChange() {
    state = {...state, players: state.players.map(p => p.id === 1 ? {...p, id: 4} : p),
        lineups: [{...state.lineups[0], remainingSubstitutions: 0,
            starters: [player(4, 'Suplente A'), ...state.lineups[0].starters.slice(1)],
            substitutes: [player(1, 'Titular A'), ...state.lineups[0].substitutes.slice(1)]}, state.lineups[1]],
        events: [{eventId: 'applied-1', type: 'SUBSTITUTION_APPLIED', pauseId: `42:${state.breakIndex}`,
            clubId: 1, outPlayerId: 1, inPlayerId: 4}]};
}

it.each([1, 2, 3])('permite pedir un cambio para la pausa actual %s y espera al motor', async index => {
    pause(index);
    const before = structuredClone(state);
    const view = render(panel());
    expect(screen.getByText(/El cambio se realizará en esta pausa:/)).toBeInTheDocument();
    expect(screen.queryByText(/Próxima pausa:/)).not.toBeInTheDocument();
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    fireEvent.click(screen.getByRole('button', {name: 'Guardando…'}));
    await screen.findByText(/Cambio pendiente:/);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/matches/42/substitutions');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({outPlayerId: 1, inPlayerId: 4, commandId: 'command-1', pauseId: `42:${index}`});
    expect(state).toEqual(before);
    expect(screen.getByRole('button', {name: 'Realizar cambio'})).toBeDisabled();
    expect(screen.queryByText(/Cambio aplicado:/)).not.toBeInTheDocument();
    view.rerender(panel({sequence: 3}));
    expect(screen.getByText(/Cambio pendiente:/)).toBeInTheDocument();
    applyChange();
    view.rerender(panel({sequence: 4}));
    expect(screen.getByText(/Cambio aplicado:/)).toBeInTheDocument();
    expect(screen.queryByText(/Cambio pendiente:/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', {name: 'Realizar cambio'})).not.toBeInTheDocument();
});

it('retira la acción cuando un cambio planificado o del DT consume la cuota', () => {
    pause();
    const view = render(panel());
    choose();
    expect(screen.getByRole('button', {name: 'Realizar cambio'})).toBeEnabled();
    applyChange();
    view.rerender(panel({sequence: 3}));
    expect(screen.getByText('No hay cambios disponibles para esta pausa.')).toBeInTheDocument();
    expect(screen.queryByRole('button', {name: 'Realizar cambio'})).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
});

it('atribuye al DT una sustitución confirmada por el motor', () => {
    pause();
    applyChange();
    state.events[0].source = 'DT';
    render(panel());
    expect(screen.getByText('El DT hizo un cambio. Salió Titular A y entró Suplente A.')).toBeInTheDocument();
});

it.each(['disconnected', 'missing-pause', 'no-substitutes'])('impide enviar cambios durante la pausa si falta: %s', reason => {
    pause();
    if (reason === 'missing-pause') state.breakIndex = null;
    if (reason === 'no-substitutes') state.lineups[0].substitutes = [];
    render(panel({connected: reason !== 'disconnected'}));
    choose();
    expect(screen.getByRole('button', {name: 'Realizar cambio'})).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
});

it.each([202, 409])('retira el panel al reanudar e ignora una respuesta tardía %s', async status => {
    pause();
    const before = structuredClone(state.players);
    let finish;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const view = render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    const signal = fetchMock.mock.calls[0][1].signal;
    state = {...state, phase: 'PLAYING', breakIndex: null, breakRemainingMs: 0};
    view.rerender(panel({sequence: 3}));
    expect(signal.aborted).toBe(true);
    expect(screen.queryByRole('region', {name: 'Sustitución durante la pausa'})).not.toBeInTheDocument();
    expect(screen.queryByRole('button', {name: 'Realizar cambio'})).not.toBeInTheDocument();
    await act(async () => finish(reply(status === 202 ? {...pending(), sequence: 2}
        : {error: {code: 'PAUSE_CLOSED', message: 'La pausa ya no está abierta.'}}, status)));
    expect(screen.queryByText(/Cambio pendiente:/)).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Guardar cambio'})).toBeEnabled();
    expect(state.players).toEqual(before);
});

it('muestra un rechazo de la pausa actual sin cambiar jugadores y permite reintentar', async () => {
    pause();
    fetchMock.mockResolvedValueOnce(reply({error: {code: 'PAUSE_CLOSED', message: 'La pausa ya no está abierta.'}}, 409));
    const before = structuredClone(state.players);
    render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('La pausa ya no está abierta.');
    expect(state.players).toEqual(before);
    expect(screen.queryByText(/Cambio aplicado:/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Realizar cambio'})).toBeEnabled();
});

it('reutiliza el comando al fallar la red y genera otro para una pausa distinta', async () => {
    pause();
    fetchMock.mockRejectedValueOnce(new TypeError('network'));
    const view = render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    await screen.findByRole('alert');
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    await screen.findByText(/Cambio pendiente:/);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(JSON.parse(fetchMock.mock.calls[1][1].body));
    pause(2);
    view.rerender(panel({sequence: 4}));
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    await screen.findByText(/Cambio pendiente:/);
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toMatchObject({pauseId: '42:2', commandId: 'command-2'});
});

it('un rechazo del motor termina el pendiente sin consumir un cambio en la interfaz', async () => {
    pause();
    const view = render(panel());
    choose();
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    await screen.findByText(/Cambio pendiente:/);
    state = {...state, events: [{eventId: 'rejected-1', type: 'SUBSTITUTION_REJECTED', clubId: 1,
        pauseId: '42:1', outPlayerId: 1, inPlayerId: 4, reason: 'SUBSTITUTION_INVALID_PLAYERS'}]};
    view.rerender(panel({sequence: 3}));
    expect(screen.queryByText(/Cambio pendiente:/)).not.toBeInTheDocument();
    expect(screen.getByText('El motor rechazó el cambio; no se aplicó.')).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Realizar cambio'})).toBeEnabled();
    fireEvent.click(screen.getByRole('button', {name: 'Realizar cambio'}));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).commandId).toBe('command-2');
    await screen.findByText(/Cambio pendiente:/);
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

it.each([false, true])('integra el panel y sólo cambia la cancha al recibir el snapshot aplicado; manual=%s', async manual => {
    if (manual) pause();
    let snapshot = {sequence: 1, state};
    useMatchConnection.mockReturnValue({snapshot, connectionStatus: 'connected', error: '', retry: vi.fn()});
    const view = render(matchPage());
    await screen.findByRole('region', {name: manual ? 'Sustitución durante la pausa' : 'Sustitución programada'});
    choose();
    fireEvent.click(screen.getByRole('button', {name: manual ? 'Realizar cambio' : 'Guardar cambio'}));
    await screen.findByText(manual ? /Cambio pendiente:/ : /Cambio planificado:/);
    expect(screen.getByTestId('cancha')).toHaveTextContent('1,2,3,7,8,9');
    expect(within(screen.getByRole('region', {name: 'Banco de Mi club'})).getByText('Suplente A')).toBeInTheDocument();
    state = {...state, players: state.players.map(p => p.id === 1 ? {...p, id: 4} : p),
        lineups: [{...state.lineups[0], remainingSubstitutions: 0,
            starters: [player(4, 'Suplente A'), ...state.lineups[0].starters.slice(1)],
            substitutes: [player(1, 'Titular A'), ...state.lineups[0].substitutes.slice(1)]}, state.lineups[1]],
        events: [{eventId: 'applied-1', type: 'SUBSTITUTION_APPLIED', clubId: 1, outPlayerId: 1, inPlayerId: 4}]};
    snapshot = {sequence: 3, state};
    useMatchConnection.mockReturnValue({snapshot, connectionStatus: 'connected', error: '', retry: vi.fn()});
    view.rerender(matchPage());
    expect(screen.getByTestId('cancha')).toHaveTextContent('4,2,3,7,8,9');
    const bench = within(screen.getByRole('region', {name: 'Banco de Mi club'}));
    expect(bench.getByText('Titular A')).toBeInTheDocument();
    expect(bench.queryByText('Suplente A')).not.toBeInTheDocument();
    expect(screen.getByText(/Cambio aplicado:/)).toBeInTheDocument();
});

it.each([false, true])('muestra las sustituciones del DT sin controles de cambio; pausa=%s', async paused => {
    if (paused) pause();
    state.teams[0] = {...state.teams[0], dtActive: true, dtConfigured: true,
        dtError: paused ? 'El programa del DT se interrumpió.' : null};
    state.lineups[0].pendingSubstitution = pending();
    state.events = [{eventId: 'dt-1', type: 'SUBSTITUTION_APPLIED', source: 'DT',
        clubId: 1, outPlayerId: 1, inPlayerId: 4}];
    useMatchConnection.mockReturnValue({snapshot: {sequence: 1, state}, connectionStatus: 'connected', error: '', retry: vi.fn()});
    render(matchPage());

    const substitutions = await screen.findByRole('region', {name: 'Sustituciones'});
    expect(substitutions).toHaveTextContent('El DT hizo un cambio. Salió Titular A y entró Suplente A.');
    expect(screen.getByRole('region', {name: 'Marcador del partido'})).toBeInTheDocument();
    expect(screen.getByTestId('cancha')).toBeInTheDocument();
    expect(screen.getByText(paused ? 'DT con error' : 'DT activo')).toBeInTheDocument();
    if (paused) expect(screen.getByRole('alert')).toHaveTextContent('El programa del DT se interrumpió.');
    expect(screen.queryByRole('button', {name: /activar DT/i})).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Titular que sale')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Suplente que entra')).not.toBeInTheDocument();
    expect(screen.queryByText(/Cambio planificado:/)).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).not.toContain('/api/matches/42/dt');
});
