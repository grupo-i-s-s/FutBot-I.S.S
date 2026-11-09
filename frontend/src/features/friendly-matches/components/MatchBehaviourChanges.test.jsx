import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import LiveChangeBehaviour from './MatchBehaviourChanges';

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

it('muestra el cambio predeterminado recibido del motor y conserva los cambios manuales', async () => {
    const behaviours = [{id: 10, name: 'Equilibrado'}, {id: 11, name: 'Defensivo'}];
    const player = {id: 1, name: 'Jugador', behaviourId: 10, behaviourMode: 'BALANCED'};
    const roster = updated => (
        <LiveChangeBehaviour matchId="42" players={[updated]} behaviours={behaviours} isMyTeam canChange />
    );
    const fetchMock = vi.fn(async () => ({
        ok: true, status: 200, json: async () => ({queued: true}),
    }));
    vi.stubGlobal('fetch', fetchMock);
    const view = render(roster(player));
    const select = screen.getByRole('combobox', {name: 'Cambiar táctica de Jugador (#1)'});
    expect(select).toHaveValue('10');
    view.rerender(roster({...player, behaviourId: 11, behaviourMode: 'DEFENSIVE'}));
    expect(select).toHaveValue('11');

    fireEvent.change(select, {target: {value: '10'}});
    expect(fetchMock).toHaveBeenCalledWith('/api/matches/42/live_request', expect.objectContaining({
        method: 'POST', body: JSON.stringify({player_id: 1, behaviour_id: 10}),
    }));
    expect(await screen.findByRole('combobox')).toHaveValue('11');
});
