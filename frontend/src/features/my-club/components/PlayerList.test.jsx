import {render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {describe, expect, it} from 'vitest';

import PlayerList from './PlayerList';

describe('PlayerList', () => {
    it('muestra los atributos PACSS y el comportamiento del jugador como información', () => {
        render(
            <PlayerList
                players={[
                    {
                        id: 1,
                        name: 'Marta',
                        power: 80,
                        agility: 75,
                        control: 90,
                        speed: 85,
                        strength: 78,
                        behaviourName: 'Ofensivo',
                    },
                ]}
            />,
            {wrapper: MemoryRouter},
        );

        expect(screen.getByText('Marta')).toBeInTheDocument();
        for (const [attribute, value] of [
            ['Power', 80], ['Agility', 75], ['Control', 90],
            ['Speed', 85], ['Strength', 78],
        ]) {
            expect(screen.getByText(`${attribute}:`).parentElement)
                .toHaveTextContent(`${attribute}: ${value}`);
        }
        expect(screen.getByText('Ofensivo')).toBeInTheDocument();
        expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    });

    it('muestra un estado vacío cuando no hay jugadores', () => {
        render(
            <PlayerList players={[]}/>,
            {wrapper: MemoryRouter},
        );

        expect(screen.getByText('Sin jugadores')).toBeInTheDocument();
        expect(
            screen.getByText('El club todavía no tiene jugadores.')
        ).toBeInTheDocument();
    });
});
