import {act, cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import {afterEach, expect, it, vi} from 'vitest';
import {SessionProvider} from '../session/SessionProvider.jsx';
import MatchPage from './MatchPage.jsx';
import {useMatchConnection} from './hooks/useMatchConnection.js';

vi.mock('./hooks/useMatchConnection.js', () => ({useMatchConnection: vi.fn()}));
vi.mock('./components/MatchCanvas.jsx', () => ({default: () => null}));

const behaviours = [{id: 7, name: 'Equilibrado'}, {id: 8, name: 'Defensivo'}];
const selectorName = 'Cambiar táctica de Julia (#11)';

function jsonResponse(body, status = 200) {
    return {ok: status < 400, status, json: async () => body};
}

function showSnapshot({status = 'RUNNING', behaviourId = 7, phase, connectionStatus,
    localDt = {dtActive: false}, visitorDt = {dtActive: false}} = {}) {
    useMatchConnection.mockReturnValue({
        connectionStatus: connectionStatus ?? (status === 'RUNNING' ? 'connected' : 'finished'),
        snapshot: {state: {
            status, phase, breakRemainingMs: 5_000, clockMs: 10_000, durationMs: 300_000,
            teams: [{id: 1, name: 'Club local', score: 0, ...localDt},
                {id: 2, name: 'Club visitante', score: 0, ...visitorDt}],
            players: [
                {id: 11, teamId: 1, name: 'Julia', behaviourId},
                {id: 12, teamId: 1, name: 'Inés', behaviourId: 7},
                {id: 21, teamId: 2, name: 'Bruno', behaviourId: 17},
            ],
        }},
    });
}

function renderMatch(state) {
    function page() {
        return (
            <MemoryRouter initialEntries={[{pathname: '/partidos/42', state}]}>
                <SessionProvider>
                    <Routes><Route path="/partidos/:matchId" element={<MatchPage/>}/></Routes>
                </SessionProvider>
            </MemoryRouter>
        );
    }
    const view = render(page());
    return () => view.rerender(page());
}

function mockRequests(sendOrder, club = {id: 1}) {
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
        if (url === '/api/clubs/me') return jsonResponse(club);
        if (url === '/api/behaviours') return jsonResponse({items: behaviours});
        if (url === '/api/matches/42/live-requests') return sendOrder(options);
        throw new Error(`Solicitud inesperada: ${url}`);
    }));
}

async function getSelector() {
    const selector = await screen.findByRole('combobox', {name: selectorName});
    await within(selector).findByRole('option', {name: 'Defensivo'});
    return selector;
}

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
});

it.each([
    ['red', () => { throw new TypeError('offline'); }, 'No se pudo conectar con el servidor.'],
    ['API', () => jsonResponse({error: {code: 'BEHAVIOUR_INVALID', message: 'Orden rechazada.'}}, 409), 'Orden rechazada.'],
])('recupera el valor confirmado y permite reintentar ante un error de %s', async (_, failOrder, message) => {
    const firstOrder = Promise.withResolvers();
    const sendOrder = vi.fn()
        .mockImplementationOnce(async () => {
            await firstOrder.promise;
            return failOrder();
        })
        .mockResolvedValueOnce(jsonResponse({queued: true, requestId: 2}));
    mockRequests(sendOrder);
    showSnapshot();
    renderMatch();
    const selector = await getSelector();

    fireEvent.change(selector, {target: {value: '8'}});
    expect(selector).toBeDisabled();
    expect(selector).toHaveValue('7');
    expect(screen.getByText('Enviando orden…')).toBeInTheDocument();
    expect(screen.getByRole('combobox', {name: 'Cambiar táctica de Inés (#12)'})).toBeEnabled();

    await act(async () => firstOrder.resolve());
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(selector).toHaveValue('7');
    expect(selector).toBeEnabled();

    fireEvent.change(selector, {target: {value: '8'}});
    await waitFor(() => expect(selector).toBeEnabled());
    expect(sendOrder).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('muestra la táctica aceptada cuando la confirma el partido', async () => {
    const sendOrder = vi.fn().mockResolvedValue(jsonResponse({queued: true, requestId: 1}));
    mockRequests(sendOrder);
    showSnapshot();
    const rerender = renderMatch();
    const selector = await getSelector();

    fireEvent.change(selector, {target: {value: '8'}});
    await waitFor(() => expect(selector).toBeEnabled());
    expect(sendOrder).toHaveBeenCalledWith(expect.objectContaining({
        method: 'POST', body: JSON.stringify({playerId: 11, behaviourId: 8}),
    }));
    expect(selector).toHaveValue('7');

    showSnapshot({behaviourId: 8});
    rerender();
    expect(selector).toHaveValue('8');
    const label = within(selector.closest('li')).getByText('Comportamiento actual:');
    expect(label.parentElement).toHaveTextContent('Comportamiento actual: Defensivo');
});

it('solo habilita cambios del equipo propio mientras el partido está en curso', async () => {
    const sendOrder = vi.fn();
    mockRequests(sendOrder);
    showSnapshot({phase: 'HALF_BREAK'});
    const rerender = renderMatch();
    const selector = await getSelector();
    expect(selector).toBeEnabled();
    expect(screen.queryByRole('combobox', {name: /Bruno/})).not.toBeInTheDocument();

    showSnapshot({status: 'FINISHED'});
    rerender();
    expect(selector).toBeDisabled();
    fireEvent.change(selector, {target: {value: '8'}});
    expect(sendOrder).not.toHaveBeenCalled();
});

it('espera el modo del snapshot y muestra los cambios del DT sin selector manual en un amistoso', async () => {
    const sendOrder = vi.fn();
    mockRequests(sendOrder, {id: 1, dt: {isActive: false}});
    showSnapshot({localDt: {dtConfigured: true}});
    const rerender = renderMatch({returnTo: '/partidos-disponibles'});

    const lineups = await screen.findByRole('region', {name: 'Jugadores en cancha'});
    await within(lineups).findAllByText('Comportamiento actual:');
    expect(within(lineups).queryByRole('combobox')).not.toBeInTheDocument();

    showSnapshot({localDt: {dtActive: true}, behaviourId: 8, connectionStatus: 'reconnecting'});
    rerender();
    expect(screen.getByText('Estás viendo el partido en modo espectador.')).toBeInTheDocument();
    const player = screen.getByRole('heading', {name: '#11 Julia'}).closest('li');
    await waitFor(() => expect(player).toHaveTextContent('Comportamiento actual: Defensivo'));
    expect(within(lineups).queryByRole('combobox')).not.toBeInTheDocument();
    expect(sendOrder).not.toHaveBeenCalled();
});

it('conserva el control del rival manual en liga aunque su perfil de club tenga el DT activado', async () => {
    const sendOrder = vi.fn().mockResolvedValue(jsonResponse({queued: true, requestId: 1}));
    mockRequests(sendOrder, {id: 2, dt: {isActive: true}});
    const localDt = {dtActive: true};
    const visitorDt = {dtActive: false, dtConfigured: true, dtError: 'Error anterior'};
    showSnapshot({localDt, visitorDt, connectionStatus: 'reconnecting'});
    const rerender = renderMatch({returnTo: '/ligas/14/sala-de-espera'});

    const selector = await screen.findByRole('combobox', {name: 'Cambiar táctica de Bruno (#21)'});
    await within(selector).findByRole('option', {name: 'Defensivo'});
    expect(selector).toBeDisabled();
    expect(screen.queryByText('Error anterior')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox', {name: selectorName})).not.toBeInTheDocument();

    showSnapshot({localDt, visitorDt});
    rerender();
    expect(selector).toBeEnabled();
    fireEvent.change(selector, {target: {value: '8'}});
    await waitFor(() => expect(sendOrder).toHaveBeenCalledWith(expect.objectContaining({
        method: 'POST', body: JSON.stringify({playerId: 21, behaviourId: 8}),
    })));
});
