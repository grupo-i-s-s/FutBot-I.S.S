import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import CreateLeaguePage from './CreateLeaguePage.jsx';
import {MemoryRouter, Route, Routes} from 'react-router';

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function submitLeague() {
    render(
        <MemoryRouter initialEntries={['/crear-liga']}>
            <Routes>
                <Route
                    path="/crear-liga"
                    element={<CreateLeaguePage/>}
                />
                <Route
                    path="/leagues/42/lobby"
                    element={<h1>Lobby de la liga creada</h1>}
                />
            </Routes>
        </MemoryRouter>
    );
    fireEvent.change(screen.getByLabelText('Nombre de la liga'), {
        target: {value: 'Liga de prueba'},
    });
    fireEvent.change(screen.getByLabelText('Maximo de clubes'), {
        target: {value: '8'},
    });
    fireEvent.change(screen.getByLabelText('Fecha y hora de inicio'), {
        target: {value: '2030-01-01T12:00'},
    });
    fireEvent.submit(screen.getByRole('button', {name: 'Crear liga'}).closest('form'));
}

it('creates a public league with the API field names and displays success', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => ({leagueId: 42, message: 'Liga creada exitosamente.'}),
    });
    vi.stubGlobal('fetch', fetchMock);
    submitLeague();

    expect(await screen.findByRole('heading', {name: 'Lobby de la liga creada'})).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/leagues/public');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
        name: 'Liga de prueba',
        min_teams: 3,
        max_teams: 8,
        start_date: new Date('2030-01-01T12:00').toISOString(),
        round_interval: 'CONTINUOUS',
    });
    expect(screen.queryByRole('button', {name: 'Crear liga'})).not.toBeInTheDocument();
});

it('displays validation errors and allows another submission', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({
            error: {
                code: 'VALIDATION_ERROR',
                message: 'Revisá los datos ingresados.',
                fields: {start_date: 'La fecha de inicio debe ser futura.'},
            },
        }),
    }));
    submitLeague();

    expect((await screen.findByRole('alert')).textContent).toBe('La fecha de inicio debe ser futura.');
    expect(screen.getByRole('button', {name: 'Crear liga'}).disabled).toBe(false);
});
