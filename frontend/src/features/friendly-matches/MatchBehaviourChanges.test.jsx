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

function showSnapshot({status = 'RUNNING', behaviourId = 7, phase} = {}) {
    useMatchConnection.mockReturnValue({
        connectionStatus: status === 'RUNNING' ? 'connected' : 'finished',
        snapshot: {state: {
            status, phase, breakRemainingMs: 5_000, clockMs: 10_000, durationMs: 300_000,
            teams: [{id: 1, name: 'Club local', score: 0}, {id: 2, name: 'Club visitante', score: 0}],
            players: [
                {id: 11, teamId: 1, name: 'Julia', behaviourId},
                {id: 12, teamId: 1, name: 'Inés', behaviourId: 7},
                {id: 21, teamId: 2, name: 'Bruno', behaviourId: 17},
            ],
        }},
    });
}

function renderMatch() {
    function page() {
        return (
            <MemoryRouter initialEntries={['/partidos/42']}>
                <SessionProvider>
                    <Routes><Route path="/partidos/:matchId" element={<MatchPage/>}/></Routes>
                </SessionProvider>
            </MemoryRouter>
        );
    }
    const view = render(page());
    return () => view.rerender(page());
}

function mockRequests(sendOrder) {
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
        if (url === '/api/clubs/me') return jsonResponse({id: 1});
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
