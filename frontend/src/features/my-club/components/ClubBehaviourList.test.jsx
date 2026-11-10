import {useState} from 'react';
import {act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {createMemoryRouter, RouterProvider} from 'react-router';
import {toast} from 'sonner';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {deleteBehaviour, getBehaviour, getBehaviourUsage, updateBehaviour} from '../../behaviours/api.js';
import ClubBehaviourList from './ClubBehaviourList.jsx';

vi.mock('../../behaviours/api.js', () => ({
    createBehaviourTestMatch: vi.fn(),
    deleteBehaviour: vi.fn(),
    getBehaviour: vi.fn(),
    getBehaviourUsage: vi.fn(),
    updateBehaviour: vi.fn(),
}));
vi.mock('../../create-behaviour/CreateBehaviourDialog.jsx', () => ({default: () => null}));
vi.mock('@monaco-editor/react', () => ({default: () => null}));
vi.mock('sonner', () => ({toast: {success: vi.fn(), error: vi.fn()}}));

const offensive = {id: 1, name: 'Ofensivo', description: 'Ataque rápido', kind: 'PLAYER', version: 1, code: 'return'};

function renderCatalogue(behaviour = offensive) {
    function Catalogue() {
        const [behaviours, setBehaviours] = useState([behaviour]);

        return (
            <ClubBehaviourList
                behaviours={behaviours}
                onDeleted={(id) => setBehaviours((current) => current.filter((item) => item.id !== id))}
            />
        );
    }

    const router = createMemoryRouter([{path: '/mi-club', element: <Catalogue/>}], {
        initialEntries: ['/mi-club?tab=behaviours'],
    });
    render(<RouterProvider router={router}/>);
}

async function openDeletion() {
    renderCatalogue();
    const cardTitle = screen.getByText(offensive.name);
    fireEvent.click(screen.getByRole('button', {name: 'Eliminar Ofensivo'}));
    const dialog = await screen.findByRole('dialog');
    return {dialog, cardTitle};
}

function confirmButton(dialog) {
    return within(dialog).getByRole('button', {name: 'Eliminar', exact: true});
}

describe('Edición y eliminación de comportamientos en Mi club', () => {
    beforeEach(() => vi.resetAllMocks());

    it('consulta si el comportamiento está en uso y permite editar cuando termina el partido', async () => {
        const behaviour = {...offensive, id: 7, name: 'Ataque propio'};
        getBehaviour.mockResolvedValueOnce(behaviour);
        getBehaviourUsage
            .mockResolvedValueOnce({inUse: true, references: {'matches.42': 'Partido activo #42'}})
            .mockResolvedValueOnce({inUse: false, references: {}});
        renderCatalogue(behaviour);

        expect(getBehaviourUsage).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole('button', {name: 'Editar Ataque propio'}));

        const dialog = within(await screen.findByRole('dialog'));
        expect(await dialog.findByText('Partido activo #42')).toBeInTheDocument();
        expect(dialog.getByRole('button', {name: 'Guardar cambios'})).toBeDisabled();
        fireEvent.click(dialog.getByRole('button', {name: 'Comprobar nuevamente'}));

        await waitFor(() => expect(dialog.getByRole('button', {name: 'Guardar cambios'})).toBeEnabled());
        expect(dialog.queryByText('Partido activo #42')).not.toBeInTheDocument();
        expect(getBehaviourUsage.mock.calls.map(([id]) => id)).toEqual([7, 7]);
    });

    it('explica la protección de un comportamiento base del DT y bloquea el guardado', async () => {
        const behaviour = {...offensive, name: 'Estrategia base', kind: 'DT'};
        getBehaviour.mockResolvedValueOnce(behaviour);
        getBehaviourUsage.mockResolvedValueOnce({
            inUse: true,
            references: {dtPreset: 'Comportamiento predeterminado del DT'},
        });
        renderCatalogue(behaviour);

        fireEvent.click(screen.getByRole('button', {name: 'Editar Estrategia base'}));

        const dialog = within(await screen.findByRole('dialog'));
        expect(await dialog.findByText('Este comportamiento base del DT está protegido.')).toBeInTheDocument();
        expect(dialog.getByRole('button', {name: 'Guardar cambios'})).toBeDisabled();
        expect(dialog.queryByRole('button', {name: 'Comprobar nuevamente'})).not.toBeInTheDocument();
        expect(updateBehaviour).not.toHaveBeenCalled();
    });

    it('cancela la eliminación sin enviar DELETE ni quitar la tarjeta', async () => {
        const {dialog, cardTitle} = await openDeletion();
        expect(within(dialog).getByText('“Ofensivo”')).toBeInTheDocument();

        fireEvent.click(within(dialog).getByRole('button', {name: 'Cancelar'}));

        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
        expect(deleteBehaviour).not.toHaveBeenCalled();
        expect(cardTitle).toBeInTheDocument();
    });

    it('mantiene la tarjeta hasta que termina DELETE y confirma la eliminación', async () => {
        let finishDelete;
        deleteBehaviour.mockReturnValueOnce(new Promise((resolve) => { finishDelete = resolve; }));
        const {dialog, cardTitle} = await openDeletion();

        fireEvent.click(confirmButton(dialog));

        expect(deleteBehaviour).toHaveBeenCalledExactlyOnceWith(offensive.id);
        expect(cardTitle).toBeInTheDocument();
        expect(within(dialog).getByRole('button', {name: 'Eliminando…'})).toBeDisabled();
        expect(within(dialog).getByRole('button', {name: 'Cancelar'})).toBeDisabled();
        expect(toast.success).not.toHaveBeenCalled();

        await act(async () => finishDelete(null));

        expect(cardTitle).not.toBeInTheDocument();
        expect(screen.getByText('Sin comportamientos')).toBeInTheDocument();
        expect(toast.success).toHaveBeenCalledExactlyOnceWith('Comportamiento eliminado', {description: offensive.name});
    });

    it('conserva la tarjeta e indica dónde reasignar un comportamiento en uso', async () => {
        deleteBehaviour.mockRejectedValueOnce(Object.assign(new Error('El comportamiento está en uso.'), {
            status: 409,
            code: 'BEHAVIOUR_IN_USE',
            fields: {
                'players.101': 'Jugador Messi (#101)',
                defaultTeam: 'Equipo predeterminado',
            },
        }));
        const {dialog, cardTitle} = await openDeletion();

        fireEvent.click(confirmButton(dialog));

        const alert = await within(dialog).findByRole('alert');
        expect(alert).toHaveTextContent('Este comportamiento está en uso.');
        expect(alert).toHaveTextContent('Debés reasignarlo antes de poder eliminarlo.');
        expect(alert).toHaveTextContent('Jugador Messi (#101)');
        expect(alert).toHaveTextContent('Equipo predeterminado');
        expect(dialog).toBeInTheDocument();
        expect(cardTitle).toBeInTheDocument();
        expect(toast.success).not.toHaveBeenCalled();
    });

    it('conserva la tarjeta si falla la red y permite reintentar la eliminación', async () => {
        const message = 'No se pudo conectar con el servidor.';
        deleteBehaviour
            .mockRejectedValueOnce(Object.assign(new Error(message), {status: 0, code: 'NETWORK_ERROR'}))
            .mockResolvedValueOnce(null);
        const {dialog, cardTitle} = await openDeletion();

        fireEvent.click(confirmButton(dialog));

        expect(await within(dialog).findByRole('alert')).toHaveTextContent(message);
        expect(cardTitle).toBeInTheDocument();
        expect(toast.error).toHaveBeenCalledExactlyOnceWith(
            'No se pudo eliminar el comportamiento', expect.objectContaining({description: message}),
        );

        const retry = confirmButton(dialog);
        expect(retry).toBeEnabled();
        fireEvent.click(retry);

        await waitFor(() => expect(cardTitle).not.toBeInTheDocument());
        expect(deleteBehaviour.mock.calls).toEqual([[offensive.id], [offensive.id]]);
    });
});
