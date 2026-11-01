import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import {LeagueLobby} from './CreateLeagueLobby.jsx';

let lobby;
let fixture;
let clubId;
let start;
let fetchMock;

beforeEach(() => {
    clubId = 1;
    lobby = {
        id: 42, name: 'Liga de prueba', status: 'open', isPrivate: false,
        creatorClubId: 1, creatorClub: {id: 1, name: 'Mi club'},
        minTeams: 3, maxTeams: 4, registeredTeams: 3, remainingSlots: 1,
        isRegistered: true, clubs: [{id: 1, name: 'Mi club'}, {id: 2, name: 'Rival'}, {id: 3, name: 'Otro club'}],
        standings: [{clubId: 1, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0}],
    };
    const match = {
        matchId: 10, creatorClubId: 1, visitorClubId: 2,
        creatorClubName: 'Mi club', visitorClubName: 'Rival',
        status: 'SCHEDULED', localScore: 0, visitorScore: 0,
    };
    fixture = {
        leagueId: 42,
        rounds: [
            {number: 1, scheduledAt: '2030-01-01T15:00:00Z', scheduleConfirmed: true, byeClubId: 3, matches: [match]},
            {number: 2, scheduledAt: '2030-01-02T15:00:00Z', scheduleConfirmed: false, byeClubId: 1,
                matches: [{...match, matchId: 11, creatorClubId: 2, creatorClubName: 'Rival', visitorClubId: 3, visitorClubName: 'Otro club'}]},
        ],
        nextMatch: {...match, roundNumber: 1, scheduledAt: '2030-01-01T15:00:00Z', scheduleConfirmed: true},
    };
    start = vi.fn(async () => {
        lobby = {...lobby, status: 'running'};
        return {leagueId: 42, status: 'running'};
    });
    fetchMock = vi.fn(async (url, options) => {
        let data;
        if (url === '/api/auth/me') data = {clubId};
        else if (url.endsWith('/lobby')) data = lobby;
        else if (url.endsWith('/fixture')) data = fixture;
        else if (url.endsWith('/start')) data = await start();
        else throw new Error(`Petición inesperada: ${url}`);
        return {ok: true, status: 200, json: async () => data};
    });
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

function openLobby() {
    render(<MemoryRouter initialEntries={['/leagues/42/lobby']}>
        <Routes><Route path="/leagues/:id/lobby" element={<LeagueLobby/>}/></Routes>
    </MemoryRouter>);
}

it('permite iniciar sólo al creador y muestra fixture, posiciones y estado actualizado', async () => {
    openLobby();
    fireEvent.click(await screen.findByRole('button', {name: 'Iniciar liga'}));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('cierran las inscripciones'));
    expect(await screen.findByText('En curso')).toBeInTheDocument();
    expect(await screen.findByRole('heading', {name: 'Tu próximo partido'})).toBeInTheDocument();
    expect(within(screen.getByRole('region', {name: 'Tabla de posiciones'})).getAllByRole('row')).toHaveLength(2);
    expect(screen.queryByRole('button', {name: 'Iniciar liga'})).not.toBeInTheDocument();
    const [, options] = fetchMock.mock.calls.find(([url]) => url.endsWith('/start'));
    expect(options.method).toBe('POST');
    expect(options.credentials).toBe('same-origin');
});

it('oculta el inicio a otros participantes', async () => {
    clubId = 2;
    openLobby();
    await screen.findByText('Clubes inscriptos (3/4)');
    expect(screen.queryByRole('button', {name: 'Iniciar liga'})).not.toBeInTheDocument();
});

it('no permite iniciar cuando faltan clubes', async () => {
    lobby.registeredTeams = 2;
    openLobby();
    expect(await screen.findByRole('button', {name: 'Iniciar liga'})).toBeDisabled();
    expect(screen.getByText('Clubes inscriptos: 2. Mínimo para iniciar: 3.')).toBeInTheDocument();
});

it('cancelar la confirmación no envía el inicio', async () => {
    window.confirm.mockReturnValue(false);
    openLobby();
    fireEvent.click(await screen.findByRole('button', {name: 'Iniciar liga'}));
    expect(start).not.toHaveBeenCalled();
});

it('evita un segundo envío mientras espera la confirmación del servidor', async () => {
    let finish;
    start.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    openLobby();
    const button = await screen.findByRole('button', {name: 'Iniciar liga'});
    fireEvent.click(button);
    fireEvent.click(button);
    expect(screen.getByRole('button', {name: 'Iniciando…'})).toBeDisabled();
    expect(start).toHaveBeenCalledTimes(1);
    lobby.status = 'running';
    await act(async () => finish({leagueId: 42, status: 'running'}));
    await screen.findByText('En curso');
});

it('muestra el rechazo del servidor y conserva el lobby abierto', async () => {
    const original = fetchMock.getMockImplementation();
    fetchMock.mockImplementation((url, options) => url.endsWith('/start')
        ? Promise.resolve({ok: false, status: 409, json: async () => ({detail: 'Una alineación está incompleta.'})})
        : original(url, options));
    openLobby();
    fireEvent.click(await screen.findByRole('button', {name: 'Iniciar liga'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Una alineación está incompleta.');
    expect(screen.getByText('Abierta')).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Iniciar liga'})).toBeEnabled();
});

it('muestra rival, fecha local, estados y resultados por ronda', async () => {
    lobby.status = 'running';
    fixture.rounds[0].matches.push({...fixture.rounds[0].matches[0], matchId: 15, status: 'RUNNING', localScore: 2, visitorScore: 1});
    fixture.rounds[0].matches.push({...fixture.rounds[0].matches[0], matchId: 16, status: 'FINISHED', localScore: 3, visitorScore: 0});
    openLobby();
    const select = await screen.findByRole('combobox', {name: 'Ronda'});
    expect(screen.getByText('Ronda 1: contra Rival.')).toBeInTheDocument();
    expect(screen.getByText('Pendiente')).toBeInTheDocument();
    expect(screen.getByText('En juego')).toBeInTheDocument();
    expect(screen.getByText('Finalizado')).toBeInTheDocument();
    expect(screen.getByText('2 - 1')).toBeInTheDocument();
    expect(screen.getByText('3 - 0')).toBeInTheDocument();
    const times = document.querySelectorAll('time');
    expect(times[0]).toHaveAttribute('datetime', '2030-01-01T15:00:00Z');
    expect(times[0]).toHaveTextContent(new Date('2030-01-01T15:00:00Z').toLocaleString('es-AR'));
    fireEvent.change(select, {target: {value: '2'}});
    expect(screen.getByText(/Horario previsto/)).toBeInTheDocument();
    expect(screen.getByText('Descansa: Mi club.')).toBeInTheDocument();
});

it('informa el descanso y el próximo partido de una ronda posterior', async () => {
    lobby.status = 'running';
    fixture.rounds[0].byeClubId = 1;
    fixture.rounds[0].matches[0] = {...fixture.rounds[1].matches[0]};
    fixture.nextMatch.roundNumber = 2;
    openLobby();
    expect(await screen.findByText('Tu club descansa en la ronda 1.')).toBeInTheDocument();
    expect(screen.getByText('Ronda 2: contra Rival.')).toBeInTheDocument();
});

it('informa la liga finalizada sin mostrar otro próximo partido', async () => {
    lobby.status = 'finished';
    fixture.nextMatch = null;
    openLobby();
    expect(await screen.findByText('La liga finalizó.')).toBeInTheDocument();
    expect(screen.queryByRole('heading', {name: 'Tu próximo partido'})).not.toBeInTheDocument();
});

it('permite reintentar un error al cargar el fixture', async () => {
    const original = fetchMock.getMockImplementation();
    let failed = false;
    fetchMock.mockImplementation(async (url, options) => {
        if (url.endsWith('/fixture') && !failed) {
            failed = true;
            throw new Error('Sin conexión');
        }
        return original(url, options);
    });
    lobby.status = 'running';
    openLobby();
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor.');
    fireEvent.click(screen.getByRole('button', {name: 'Reintentar fixture'}));
    expect(await screen.findByRole('combobox', {name: 'Ronda'})).toBeInTheDocument();
});

it('refresca por foco y eventos de liga conservando la ronda seleccionada', async () => {
    lobby.status = 'running';
    openLobby();
    fireEvent.change(await screen.findByRole('combobox', {name: 'Ronda'}), {target: {value: '2'}});
    const count = () => fetchMock.mock.calls.filter(([url]) => url.endsWith('/fixture')).length;
    const before = count();
    fireEvent(window, new Event('focus'));
    await waitFor(() => expect(count()).toBe(before + 1));
    expect(screen.getByRole('combobox', {name: 'Ronda'})).toHaveValue('2');
    fireEvent(window, new CustomEvent('league-updated', {detail: {leagueId: 99}}));
    expect(count()).toBe(before + 1);
    fireEvent(window, new CustomEvent('league-updated', {detail: {leagueId: 42}}));
    await waitFor(() => expect(count()).toBe(before + 2));
    expect(screen.getByRole('combobox', {name: 'Ronda'})).toHaveValue('2');
});
