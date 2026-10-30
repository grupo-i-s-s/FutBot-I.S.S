import {cleanup, render, screen} from '@testing-library/react';
import {afterEach, expect, it} from 'vitest';
import MatchScoreboard from './MatchScoreboard.jsx';

afterEach(cleanup);

it('mantiene identidad y resultado de los clubes después del cambio de arco', () => {
    render(<MatchScoreboard state={{
        clockMs: 150000,
        durationMs: 300000,
        teams: [
            {id: 1, name: 'Club local', side: 'RIGHT', score: 2},
            {id: 2, name: 'Club visitante', side: 'LEFT', score: 1},
        ],
    }}/>);
    expect(screen.getByText('Local').parentElement).toHaveTextContent('Club local');
    expect(screen.getByText('Visitante').parentElement).toHaveTextContent('Club visitante');
    expect(screen.getByLabelText('Marcador: 2 a 1')).toBeInTheDocument();
});
