import {afterEach, expect, it, vi} from 'vitest';
import {act, cleanup, render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import MatchesPage from './Matches.jsx';
import AvailableFriendlyMatches from '../home-page/components/AvailableFriendlyMatches.jsx';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const pages = [MatchesPage, AvailableFriendlyMatches];

function show(Component, items) {
    vi.stubGlobal('fetch', vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({items, total: items.length, page: 1, pageSize: 20}),
    })));
    render(<MemoryRouter><Component/></MemoryRouter>);
}

it.each(pages)('muestra los amistosos de la respuesta paginada en %s', async Component => {
    show(Component, [{matchId: 42, creatorClubName: 'Club visitante', startDateTime: '2030-01-01T12:00:00Z'}]);
    expect(await screen.findByText('Club visitante')).toBeInTheDocument();
    expect(screen.queryByText('No hay partidos disponibles.')).not.toBeInTheDocument();
});

it('conserva el mensaje de listado vacío en Amistosos', async () => {
    show(MatchesPage, []);
    expect(await screen.findByText('No hay partidos disponibles.')).toBeInTheDocument();
});

it('muestra los accesos de Inicio sin buscador ni mensaje de lista vacía', async () => {
    await act(async () => show(AvailableFriendlyMatches, []));

    expect(screen.getByRole('link', {name: 'Ver amistosos disponibles'})).toHaveAttribute('href', '/partidos-disponibles');
    expect(screen.getByRole('link', {name: 'Crear Partido Amistoso'})).toHaveAttribute('href', '/crear-partido');
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByText('No hay partidos disponibles.')).not.toBeInTheDocument();
});
