import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import MatchesPage from './Matches.jsx';
import AvailableFriendlyMatches from '../home-page/components/AvailableFriendlyMatches.jsx';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const pages = [MatchesPage, AvailableFriendlyMatches];

function show(Component, items) {
    vi.stubGlobal('fetch', vi.fn(async url => {
        const result = url === '/api/friendly-matches/me' ? []
            : {items, total: items.length, page: 1, pageSize: 20};
        return {ok: true, status: 200, json: async () => result};
    }));
    render(<MemoryRouter><Component/></MemoryRouter>);
}

it.each(pages)('muestra los amistosos de la respuesta paginada en %s', async Component => {
    show(Component, [{matchId: 42, creatorClubName: 'Club visitante', startDateTime: '2030-01-01T12:00:00Z'}]);
    expect(await screen.findByText('Club visitante')).toBeInTheDocument();
    expect(screen.queryByText('No hay partidos disponibles.')).not.toBeInTheDocument();
});

it.each(pages)('conserva el mensaje de listado vacío en %s', async Component => {
    show(Component, []);
    expect(await screen.findByText('No hay partidos disponibles.')).toBeInTheDocument();
});
