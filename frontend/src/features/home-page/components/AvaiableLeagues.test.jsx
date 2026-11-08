import {cleanup, render, screen, within} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {afterEach, expect, it, vi} from 'vitest';
import AvaiableLeagues from './AvaiableLeagues';

const league = {
    id: 42,
    name: 'Liga de prueba',
    status: 'open',
    maxTeams: 4,
    registeredCount: 2,
    availableSlots: 2,
    isMember: false,
    isPrivate: false,
};

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

async function renderLeague(overrides) {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
        items: [{...league, ...overrides}],
    }), {headers: {'Content-Type': 'application/json'}})));

    render(<MemoryRouter><AvaiableLeagues/></MemoryRouter>);
    await screen.findByRole('heading', {name: league.name});
    return screen.getByRole('listitem');
}

it.each([
    [{isMember: true, status: 'running', registeredCount: 4, availableSlots: 0}, 'Ver lobby de Liga de prueba', 'lobby'],
    [{}, 'Unirme a liga Liga de prueba', 'join'],
    [{isPrivate: true}, 'Unirme a liga Liga de prueba', 'join'],
])('muestra un único enlace enfocable según la inscripción (%j)', async (overrides, label, path) => {
    const card = await renderLeague(overrides);
    const links = within(card).getAllByRole('link');
    expect(links).toHaveLength(1);
    const [link] = links;
    expect(link).toHaveAccessibleName(label);
    expect(link).toHaveAttribute('href', `/leagues/42/${path}`);
    expect(card.querySelector('a a')).toBeNull();
    expect(link.tabIndex).toBe(0);
    link.focus();
    expect(link).toHaveFocus();
});

it.each([
    [{status: 'running'}, 'La inscripción está cerrada.'],
    [{registeredCount: 4, availableSlots: 0}, 'La liga está completa.'],
])('informa por qué no se puede inscribir (%j)', async (overrides, reason) => {
    const card = await renderLeague(overrides);
    expect(within(card).getByText(reason)).toBeInTheDocument();
    expect(within(card).queryByRole('link')).not.toBeInTheDocument();
    expect(card.querySelector('a')).toBeNull();
});
