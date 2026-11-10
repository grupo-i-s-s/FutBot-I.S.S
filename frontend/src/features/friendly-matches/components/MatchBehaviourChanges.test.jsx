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
        <LiveChangeBehaviour matchId="42" players={[updated]} behaviours={behaviours}
                             isMyTeam allowManualActions canChange />
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
    expect(fetchMock).toHaveBeenCalledWith('/api/matches/42/live-requests', expect.objectContaining({
        method: 'POST', body: JSON.stringify({playerId: 1, behaviourId: 10}),
    }));
    expect(await screen.findByRole('combobox')).toHaveValue('11');
});

it('muestra el PACSS del contrincante sin exponer su comportamiento ni controles', () => {
    render(<LiveChangeBehaviour matchId="42"
        players={[{id: 2, name: 'Rival', power: 20, agility: 40, control: 60, speed: 80, strength: 100, behaviourName: 'Táctica rival'}]}
        behaviours={[]} isMyTeam={false} allowManualActions={false} canChange={false}/>);

    const attributes = screen.getByLabelText('PACSS de Rival');
    for (const [label, value] of [['Power', 20], ['Agility', 40], ['Control', 60], ['Speed', 80], ['Strength', 100]]) {
        expect([...attributes.querySelectorAll('dt')].find(item => item.textContent === label)?.nextElementSibling)
            .toHaveTextContent(String(value));
    }
    expect(screen.queryByText('Táctica rival')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
});
