import {cleanup, render, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import MatchScoreboard from './MatchScoreboard.jsx';

beforeEach(() => {
    // jsdom no carga imágenes: simular una imagen decodificada permite verificar
    // el archivo que realmente muestra ClubAvatar, además de su nombre accesible.
    vi.stubGlobal('Image', class {
        complete = true;
        naturalWidth = 128;
    });
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function matchState() {
    return {
        clockMs: 150000,
        durationMs: 300000,
        teams: [
            {id: 1, name: 'Club local', avatar: 'avatar-03.png', side: 'LEFT', score: 2},
            {id: 2, name: 'Club visitante', avatar: 'avatar-17.png', side: 'RIGHT', score: 1},
        ],
    };
}

async function expectCrest(name, filename) {
    await waitFor(() => {
        expect(screen.getByRole('img', {name: `Escudo de ${name}`}).querySelector('img'))
            .toHaveAttribute('src', `/avatars/${filename}`);
    });
}

it('mantiene escudos, identidad y resultado de los clubes después del cambio de arco', async () => {
    const state = matchState();
    const {rerender} = render(<MatchScoreboard state={state}/>);
    await expectCrest('Club local', 'avatar-03.png');
    await expectCrest('Club visitante', 'avatar-17.png');

    rerender(<MatchScoreboard state={{
        ...state,
        teams: state.teams.map((team) => ({...team, side: team.side === 'LEFT' ? 'RIGHT' : 'LEFT'})),
    }}/>);

    expect(screen.getByText('Local').parentElement).toHaveTextContent('Club local');
    expect(screen.getByText('Visitante').parentElement).toHaveTextContent('Club visitante');
    expect(screen.getByLabelText('Marcador: 2 a 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Reloj del partido')).toHaveTextContent('02:30/ 05:00');
    await expectCrest('Club local', 'avatar-03.png');
    await expectCrest('Club visitante', 'avatar-17.png');
});

it('usa el escudo predeterminado para snapshots antiguos y avatares fuera del catálogo', async () => {
    const state = matchState();
    delete state.teams[0].avatar;
    state.teams[1].avatar = 'avatar-antiguo';
    render(<MatchScoreboard state={state}/>);

    await expectCrest('Club local', 'avatar-01.png');
    await expectCrest('Club visitante', 'avatar-01.png');
});

it('espera al rival sin asignarle el escudo de un club inexistente', async () => {
    const state = matchState();
    state.teams = state.teams.slice(0, 1);
    state.teams[0].score = 0;
    state.clockMs = 0;
    render(<MatchScoreboard state={state}/>);

    expect(screen.getByText('Esperando rival')).toBeInTheDocument();
    expect(screen.getAllByRole('img')).toHaveLength(1);
    expect(screen.getByLabelText('Marcador: 0 a 0')).toBeInTheDocument();
    await expectCrest('Club local', 'avatar-03.png');
});
