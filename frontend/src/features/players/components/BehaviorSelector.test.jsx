import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BehaviorSelector } from './BehaviorSelector'

describe('BehaviorSelector Component', () => {
  it('renders input and submit button correctly', () => {
    const mockPlayer = { id: 1, name: 'Jugador de Prueba', behavior_id: null }
    
    render(<BehaviorSelector player={mockPlayer} onBehaviourAssigned={() => {}} />)

    // Verifica que el input numérico y el botón existan en pantalla
    expect(screen.getByRole('spinbutton')).toBeDefined()
    expect(screen.getByRole('button', { name: /asignar comportamiento/i })).toBeDefined()
  })
})