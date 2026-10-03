import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import PlayerList from './PlayerList'

vi.mock('./BehaviorSelector', () => ({
    BehaviorSelector: () => <div data-testid="behavior-selector" />,
}))

describe('PlayerList', () => {
    it('muestra los atributos PACSS y el comportamiento del jugador', () => {
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
                behaviours={[]}
                onBehaviourAssigned={vi.fn()}
            />
        )

        expect(screen.getByText('Marta')).toBeInTheDocument()
        expect(screen.getByText('Power: 80')).toBeInTheDocument()
        expect(screen.getByText('Agility: 75')).toBeInTheDocument()
        expect(screen.getByText('Control: 90')).toBeInTheDocument()
        expect(screen.getByText('Speed: 85')).toBeInTheDocument()
        expect(screen.getByText('Strength: 78')).toBeInTheDocument()
        expect(screen.getByText('Ofensivo')).toBeInTheDocument()
    })

    it('muestra un estado vacío cuando no hay jugadores', () => {
        render(
            <PlayerList
                players={[]}
                behaviours={[]}
                onBehaviourAssigned={vi.fn()}
            />
        )

        expect(screen.getByText('Sin jugadores')).toBeInTheDocument()
        expect(
            screen.getByText('El club todavía no tiene jugadores.')
        ).toBeInTheDocument()
    })
})