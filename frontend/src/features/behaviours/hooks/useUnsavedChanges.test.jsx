import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {createMemoryRouter, RouterProvider} from 'react-router';
import App from '../../../App.jsx';
import {routes} from '@/routes.js';

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

it.each([routes.createBehaviour, routes.createDtBehaviour])(
    'protege el borrador de %s antes de cerrar sesión',
    async (path) => {
        const confirm = vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true);
        const fetch = vi.fn(async (url) => {
            if (url === '/api/clubs/me') {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({id: 8, name: 'Club de pruebas', avatar: 'avatar-01.png'}),
                };
            }
            if (url === '/api/auth/logout') return {ok: true, status: 204};
            throw new Error(`Solicitud inesperada: ${url}`);
        });
        vi.stubGlobal('confirm', confirm);
        vi.stubGlobal('fetch', fetch);
        const router = createMemoryRouter([{path: '*', element: <App/>}], {initialEntries: [path]});
        render(<RouterProvider router={router}/>);

        const name = await screen.findByLabelText('Nombre del comportamiento');
        fireEvent.change(name, {target: {value: 'Borrador'}});
        fireEvent.click(screen.getByRole('button', {name: 'Cerrar sesión'}));

        await waitFor(() => expect(screen.getByRole('button', {name: 'Cerrar sesión'})).toBeEnabled());
        expect(name).toHaveValue('Borrador');
        expect(router.state.location.pathname).toBe(path);
        expect(fetch).not.toHaveBeenCalledWith('/api/auth/logout', expect.anything());

        fireEvent.click(screen.getByRole('button', {name: 'Cerrar sesión'}));
        expect(await screen.findByRole('heading', {name: /inicio de sesión/i})).toBeInTheDocument();
        expect(fetch).toHaveBeenCalledWith('/api/auth/logout', expect.objectContaining({method: 'POST'}));
        expect(confirm).toHaveBeenCalledTimes(2);
    },
);
