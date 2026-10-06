import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {beforeEach, describe, expect, it, vi} from 'vitest';

import {assignPlayerBehaviour} from '../api';
import {BehaviorSelector} from './BehaviorSelector';

vi.mock('../api', () => ({assignPlayerBehaviour: vi.fn()}));

describe('BehaviorSelector', () => {
    beforeEach(() => vi.clearAllMocks());

    it('envía el comportamiento elegido y entrega el jugador actualizado', async () => {
        const updatedPlayer = {id: 3, behaviorId: 8, name: 'Marta'};
        const onBehaviourAssigned = vi.fn();
        assignPlayerBehaviour.mockResolvedValue(updatedPlayer);

        render(
            <BehaviorSelector
                player={{id: 3, name: 'Marta'}}
                behaviours={[{id: 8, name: 'Ofensivo'}]}
                onBehaviourAssigned={onBehaviourAssigned}
            />
        );

        fireEvent.change(screen.getByLabelText('Nuevo comportamiento para Marta'), {
            target: {value: '8'},
        });
        fireEvent.click(screen.getByRole('button', {name: 'Asignar'}));

        await waitFor(() => expect(assignPlayerBehaviour).toHaveBeenCalledWith(3, 8));
        expect(onBehaviourAssigned).toHaveBeenCalledWith(updatedPlayer);
    });
});
