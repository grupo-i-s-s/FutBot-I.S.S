import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';

import LeagueLineupPage from './LeagueLineupPage';
import {
    getLeagueLineup,
    getLineupCatalogs,
    updateLeagueLineup,
} from './api';


vi.mock('./api', () => ({
    getLeagueLineup: vi.fn(),
    getLineupCatalogs: vi.fn(),
    updateLeagueLineup: vi.fn(),
}));

let saved;


async function openPage() {
    render(
        <MemoryRouter initialEntries={['/ligas/7/plantel']}>
            <Routes>
                <Route
                    path="/ligas/:id/plantel"
                    element={<LeagueLineupPage/>}
                />
            </Routes>
        </MemoryRouter>,
    );

    return screen.findByLabelText('Formación');
}


beforeEach(() => {
    vi.resetAllMocks();

    saved = {
        leagueId: 7,
        leagueName: 'Liga de prueba',
        clubId: 1,
        version: 3,
        editable: true,
        lineUp: {
            formationId: 1,
            starters: [1, 2, 3].map(
                (playerId) => ({playerId, behaviourId: 10}),
            ),
            substitutes: [4, 5, 6].map(
                (playerId) => ({playerId, behaviourId: 11}),
            ),
        },
    };

    getLeagueLineup.mockResolvedValue(structuredClone(saved));

    getLineupCatalogs.mockResolvedValue({
        players: Array.from({length: 6}, (_, index) => ({
            id: index + 1,
            name: `Jugador ${index + 1}`,
            behaviorId: 10,
        })),
        behaviours: [
            {id: 10, name: 'Equilibrado'},
            {id: 11, name: 'Ofensivo'},
        ],
        formations: [
            {id: 1, name: '2-1'},
            {id: 2, name: '1-2'},
        ],
    });

    updateLeagueLineup.mockImplementation(async (id, body) => {
        const {expectedVersion, ...lineUp} = body;

        return {
            ...saved,
            version: expectedVersion + 1,
            lineUp,
        };
    });
});

afterEach(cleanup);


it('intercambia titular y suplente conservando sus comportamientos', async () => {
    const formation = await openPage();

    expect(
        screen.getByRole('heading', {name: 'Plantel de Liga de prueba'}),
    ).toBeInTheDocument();

    fireEvent.change(
        screen.getByLabelText('Jugador titular 1'),
        {target: {value: '4'}},
    );

    expect(screen.getByLabelText('Jugador suplente 1')).toHaveValue('1');
    expect(screen.getByLabelText('Comportamiento titular 1')).toHaveValue('11');
    expect(screen.getByLabelText('Comportamiento suplente 1')).toHaveValue('10');

    fireEvent.change(formation, {target: {value: '2'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar plantel'}));

    await screen.findByText(
        'Plantel guardado para el próximo partido de esta liga.',
    );

    const [leagueId, body] = updateLeagueLineup.mock.calls[0];

    expect(leagueId).toBe('7');
    expect(body).toEqual({
        formationId: 2,
        expectedVersion: 3,
        starters: [
            {playerId: 4, behaviourId: 11},
            {playerId: 2, behaviourId: 10},
            {playerId: 3, behaviourId: 10},
        ],
        substitutes: [
            {playerId: 1, behaviourId: 10},
            {playerId: 5, behaviourId: 11},
            {playerId: 6, behaviourId: 11},
        ],
    });
});


it('impide guardar posiciones incompletas', async () => {
    await openPage();

    fireEvent.change(
        screen.getByLabelText('Jugador titular 1'),
        {target: {value: ''}},
    );

    expect(
        screen.getByRole('button', {name: 'Guardar plantel'}),
    ).toBeDisabled();

    expect(updateLeagueLineup).not.toHaveBeenCalled();
});


it('conserva el borrador si falla el guardado', async () => {
    updateLeagueLineup.mockRejectedValue(new Error('Falló la conexión.'));
    const formation = await openPage();

    fireEvent.change(formation, {target: {value: '2'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar plantel'}));

    expect(await screen.findByRole('alert')).toHaveTextContent(
        'Falló la conexión.',
    );
    expect(formation).toHaveValue('2');
    expect(
        screen.getByRole('button', {name: 'Guardar plantel'}),
    ).toBeEnabled();
});


it('conserva el borrador ante 409 y recarga solamente cuando el usuario lo pide', async () => {
    updateLeagueLineup.mockRejectedValue(Object.assign(
        new Error('Otra edición cambió el plantel.'),
        {status: 409, code: 'LEAGUE_LINEUP_CONFLICT'},
    ));

    const formation = await openPage();

    fireEvent.change(formation, {target: {value: '2'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar plantel'}));

    await screen.findByRole('alert');

    expect(formation).toHaveValue('2');
    expect(getLeagueLineup).toHaveBeenCalledTimes(1);
    expect(
        screen.getByRole('button', {name: 'Guardar plantel'}),
    ).toBeDisabled();

    getLeagueLineup.mockRejectedValueOnce(new Error('No se pudo recargar.'));
    fireEvent.click(screen.getByRole('button', {name: 'Recargar plantel'}));

    expect(await screen.findByRole('alert')).toHaveTextContent(
        'No se pudo recargar.',
    );
    expect(formation).toHaveValue('2');

    getLeagueLineup.mockResolvedValueOnce({...saved, version: 9});
    fireEvent.click(screen.getByRole('button', {name: 'Recargar plantel'}));

    await waitFor(() => {
        expect(formation).toHaveValue('1');
        expect(
            screen.getByRole('button', {name: 'Guardar plantel'}),
        ).toBeEnabled();
    });

    updateLeagueLineup.mockResolvedValueOnce({...saved, version: 10});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar plantel'}));

    await waitFor(() => {
        expect(
            updateLeagueLineup.mock.calls.at(-1)[1].expectedVersion,
        ).toBe(9);
    });
});


it('permite configurar una inscripción inicial con versión cero', async () => {
    getLeagueLineup.mockResolvedValueOnce({
        ...saved,
        version: 0,
        lineUp: null,
    });

    const formation = await openPage();
    fireEvent.change(formation, {target: {value: '1'}});

    for (let index = 0; index < 6; index += 1) {
        const title = index < 3
            ? `titular ${index + 1}`
            : `suplente ${index - 2}`;

        fireEvent.change(
            screen.getByLabelText(`Jugador ${title}`),
            {target: {value: String(index + 1)}},
        );
    }

    fireEvent.click(screen.getByRole('button', {name: 'Guardar plantel'}));

    await waitFor(() => {
        expect(updateLeagueLineup.mock.calls[0][1].expectedVersion).toBe(0);
    });
});


it('muestra una liga terminada como solo lectura y conserva el ID de un comportamiento archivado', async () => {
    saved.lineUp.substitutes[0].behaviourId = 25;
    getLeagueLineup.mockResolvedValueOnce({...saved, editable: false});

    const formation = await openPage();
    const archived = screen.getByLabelText('Comportamiento suplente 1');

    expect(formation).toBeDisabled();
    expect(archived).toBeDisabled();
    expect(archived).toHaveValue('25');
    expect(archived).toHaveDisplayValue('Comportamiento guardado #25');
    expect(screen.getByLabelText('Comportamiento titular 1')).toHaveDisplayValue('Equilibrado');
    expect(screen.queryByText('Elegí un comportamiento validado para cada jugador.')).not.toBeInTheDocument();
    expect(
        screen.getByRole('button', {name: 'Guardar plantel'}),
    ).toBeDisabled();
});
