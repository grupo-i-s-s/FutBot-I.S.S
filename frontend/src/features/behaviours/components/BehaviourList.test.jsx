import {beforeEach, describe, expect, it, vi} from 'vitest';
import { act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import BehaviourList from './BehaviourList';
import {fetchBehaviours} from '../services/behavioursApi';
import {MemoryRouter, Route, Routes} from 'react-router';
import {deleteBehaviour,getBehaviourUsage, getBehaviour} from '../api';
import BehaviourDetailPage from '../BehaviourDetailPage';

// Mockeamos el servicio de API
vi.mock('../services/behavioursApi', () => ({
    fetchBehaviours: vi.fn(),
}));
vi.mock('../api', () => ({
    deleteBehaviour: vi.fn(),
    getBehaviour: vi.fn(),
    getBehaviourUsage: vi.fn(),
    updateBehaviour: vi.fn(),
    createBehaviourTestMatch: vi.fn(),
}));

async function openDeletion() {
        fetchBehaviours.mockResolvedValueOnce([
            {
                id: 1,
                name: 'Ofensivo',
                description: 'Ataque rápido',
            },
        ]);

        render(
            <MemoryRouter initialEntries={['/behaviours']}>
                <BehaviourList/>
            </MemoryRouter>
        );

        const heading = await screen.findByRole('heading', {
            name: 'Ofensivo',
        });

        fireEvent.click(
            screen.getByRole('button', {
                name: 'Eliminar Ofensivo',
            })
        );

        const dialog = await screen.findByRole('dialog');

        return {dialog, heading};
    }

    function confirmDeletion(dialog) {
        fireEvent.click(
            within(dialog).getByRole('button', {
                name: 'Eliminar',
                exact: true,
            })
        );
    }

describe('BehaviourList Component', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        getBehaviourUsage.mockResolvedValue({
            inUse: false,
            references: {},
        });
    });

    it('muestra el estado de carga y luego renderiza la lista con nombres, descripciones, marca default y enlaces de navegación', async () => {
        const mockBehaviours = [
            {id: 1, name: 'Ofensivo', description: 'Juego de ataque rápido', isDefault: true},
            {id: 2, name: 'Defensivo', description: 'Bloque bajo compacto', isDefault: false},
        ];
        fetchBehaviours.mockResolvedValueOnce(mockBehaviours);

        render(
            <MemoryRouter>
                <BehaviourList/>
            </MemoryRouter>
        );

        // Verificar estado de carga inicial
        expect(screen.getByText(/cargando catálogo/i)).toBeInTheDocument();

        // Esperar a que se rendericen los datos
        await waitFor(() => {
            expect(screen.getByText('Ofensivo')).toBeInTheDocument();
            expect(screen.getByText('Juego de ataque rápido')).toBeInTheDocument();
            expect(screen.getByText('Default')).toBeInTheDocument();
            expect(screen.getByText('Defensivo')).toBeInTheDocument();
        });

        // Verificar enlaces por ID de navegación al detalle
        const links = screen.getAllByText(/ver detalle/i);
        expect(links).toHaveLength(2);
        expect(links[0].getAttribute('href')).toBe('/behaviours/1');
        expect(links[1].getAttribute('href')).toBe('/behaviours/2');

        // Verificar los controles disponibles en el catálogo.
        expect(screen.getByRole('link', {name: 'Crear nuevo comportamiento'})).toHaveAttribute('href', '/crear-comportamiento');
        expect(screen.getByRole('button', {name: 'Eliminar Ofensivo'})).toBeInTheDocument();
    });

    it('maneja el estado de error y permite reintentar la carga', async () => {
        fetchBehaviours.mockRejectedValueOnce(new Error('Error al cargar el catálogo de comportamientos.'));

        render(
            <MemoryRouter>
                <BehaviourList/>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText(/error al cargar el catálogo/i)).toBeInTheDocument();
        });

        const retryButton = screen.getByRole('button', {name: /reintentar/i});
        expect(retryButton).toBeInTheDocument();

        // Simulamos que al reintentar ahora sí responde con éxito
        fetchBehaviours.mockResolvedValueOnce([
            {id: 1, name: 'Equilibrado', description: 'Juego mixto', isDefault: false}
        ]);

        fireEvent.click(retryButton);

        await waitFor(() => {
            expect(screen.getByText('Equilibrado')).toBeInTheDocument();
        });
    });

    it('muestra el estado vacío cuando la lista no tiene elementos', async () => {
        fetchBehaviours.mockResolvedValueOnce([]);

        render(
            <MemoryRouter>
                <BehaviourList/>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText(/no hay comportamientos disponibles/i)).toBeInTheDocument();
        });
    });
    it('cancelar no envía DELETE y conserva el comportamiento', async () => {
    const {dialog, heading} = await openDeletion();

    expect(
        within(dialog).getByText('“Ofensivo”')
    ).toBeInTheDocument();

    expect(deleteBehaviour).not.toHaveBeenCalled();

    fireEvent.click(
        within(dialog).getByRole('button', {
            name: 'Cancelar',
        })
    );

    await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    expect(deleteBehaviour).not.toHaveBeenCalled();
    expect(heading).toBeInTheDocument();
    });


    it('espera al backend, retira la tarjeta y muestra éxito', async () => {
        let resolveDelete;

        deleteBehaviour.mockReturnValueOnce(
            new Promise((resolve) => {
                resolveDelete = resolve;
            })
        );

        const {dialog, heading} = await openDeletion();

        confirmDeletion(dialog);

        expect(deleteBehaviour).toHaveBeenCalledTimes(1);
        expect(deleteBehaviour).toHaveBeenCalledWith(1);

        // La tarjeta continúa hasta que el backend confirme.
        expect(heading).toBeInTheDocument();

        expect(
            within(dialog).getByRole('button', {
                name: /eliminando/i,
            })
        ).toBeDisabled();

        // deleteBehaviour devuelve null cuando recibe un 204.
        await act(async () => {
            resolveDelete(null);
        });

        await waitFor(() => {
            expect(heading).not.toBeInTheDocument();
        });

        expect(screen.getByRole('status')).toHaveTextContent(
            'El comportamiento “Ofensivo” se eliminó correctamente.'
        );

        expect(
            screen.getByText(/no hay comportamientos disponibles/i)
        ).toBeInTheDocument();
    });


    it('un 409 conserva la tarjeta e indica dónde reasignarlo', async () => {
        deleteBehaviour.mockRejectedValueOnce(
            Object.assign(new Error('El comportamiento está en uso.'), {
                status: 409,
                code: 'BEHAVIOUR_IN_USE',
                fields: {
                    'players.101': 'Jugador Messi (#101)',
                    defaultTeam: 'Equipo predeterminado',
                },
            })
        );

        const {dialog, heading} = await openDeletion();

        confirmDeletion(dialog);

        const alert = await screen.findByRole('alert');

        expect(alert).toHaveTextContent(
            'Este comportamiento está en uso.'
        );
        expect(alert).toHaveTextContent(
            'Debés reasignarlo antes de poder eliminarlo.'
        );
        expect(alert).toHaveTextContent('Jugador Messi (#101)');
        expect(alert).toHaveTextContent('Equipo predeterminado');

        expect(heading).toBeInTheDocument();
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });


    it('un error de red conserva la tarjeta y permite reintentar', async () => {
        deleteBehaviour.mockRejectedValueOnce(
            Object.assign(
                new Error('No se pudo conectar con el servidor.'),
                {
                    status: 0,
                    code: 'NETWORK_ERROR',
                }
            )
        );

        const {dialog, heading} = await openDeletion();

        confirmDeletion(dialog);

        const alert = await screen.findByRole('alert');

        expect(alert).toHaveTextContent(
            'No se pudo conectar con el servidor.'
        );
        expect(heading).toBeInTheDocument();

        expect(
            within(dialog).getByRole('button', {
                name: 'Eliminar',
                exact: true,
            })
        ).toBeEnabled();
    });


    it('eliminar desde el detalle vuelve al catálogo con el aviso', async () => {
        getBehaviour.mockResolvedValueOnce({
            id: 1,
            name: 'Ofensivo',
            code: 'programa de prueba',
        });

        fetchBehaviours.mockResolvedValueOnce([]);
        deleteBehaviour.mockResolvedValueOnce(null);

        render(
            <MemoryRouter initialEntries={['/behaviours/1']}>
                <Routes>
                    <Route
                        path="/behaviours/:behaviourId"
                        element={<BehaviourDetailPage/>}
                    />
                    <Route
                        path="/behaviours"
                        element={<BehaviourList/>}
                    />
                </Routes>
            </MemoryRouter>
        );

        fireEvent.click(
            await screen.findByRole('button', {
                name: 'Eliminar Ofensivo',
            })
        );

        const dialog = await screen.findByRole('dialog');

        confirmDeletion(dialog);

        expect(
            await screen.findByRole('heading', {
                name: 'Catálogo de Comportamientos',
            })
        ).toBeInTheDocument();

        expect(
            screen.queryByRole('heading', {
                name: 'Detalle de comportamiento',
            })
        ).not.toBeInTheDocument();

        expect(screen.getByRole('status')).toHaveTextContent(
            'El comportamiento “Ofensivo” se eliminó correctamente.'
        );

        expect(deleteBehaviour).toHaveBeenCalledTimes(1);
        expect(deleteBehaviour).toHaveBeenCalledWith(1);
    });
});
