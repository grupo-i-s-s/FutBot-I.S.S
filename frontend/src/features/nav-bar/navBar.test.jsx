import {act, cleanup, render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import NavBar from './navBar';
import {updateMyClub} from '../my-club/api';
import {SessionProvider} from '../session/SessionProvider.jsx';

vi.mock('../my-club/components/ClubAvatar', () => ({
    default: ({avatar, clubName}) => (
        <img src={`/avatars/${avatar}`} alt={`Escudo de ${clubName}`}/>
    ),
}));

const originalClub = {
    id: 7,
    name: 'Club original',
    avatar: 'avatar-01.png',
    friendlyAvailable: true,
};

function deferred() {
    let resolve;
    let reject;
    const promise = new Promise((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return {promise, resolve, reject};
}

function jsonResponse(body, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    };
}

function renderNavBar() {
    return render(
        <MemoryRouter initialEntries={['/mi-club']}>
            <SessionProvider>
                <NavBar/>
            </SessionProvider>
        </MemoryRouter>,
    );
}

function expectClub(club) {
    expect(screen.getByRole('img', {name: `Escudo de ${club.name}`}))
        .toHaveAttribute('src', `/avatars/${club.avatar}`);
    expect(screen.getByText(club.name)).toBeInTheDocument();
}

describe('Actualización del club en la barra de navegación', () => {
    let fetchMock;

    beforeEach(() => {
        fetchMock = vi.fn();
        vi.stubGlobal('fetch', fetchMock);
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
    });

    it('espera el guardado y muestra inmediatamente el avatar y nombre devueltos por el servidor', async () => {
        const patch = deferred();
        fetchMock.mockImplementation((url, options) => {
            expect(url).toBe('/api/clubs/me');
            return options.method === 'PATCH'
                ? patch.promise
                : Promise.resolve(jsonResponse(originalClub));
        });
        renderNavBar();
        await screen.findByText(originalClub.name);

        const requestedChanges = {
            name: 'Nombre solicitado',
            avatar: 'avatar-05.png',
            friendlyAvailable: false,
        };
        const savedClub = {
            ...originalClub,
            name: 'Nombre confirmado',
            avatar: 'avatar-08.png',
            friendlyAvailable: false,
        };

        const save = updateMyClub(requestedChanges);
        expectClub(originalClub);
        expect(screen.queryByText(requestedChanges.name)).not.toBeInTheDocument();

        await act(async () => {
            patch.resolve(jsonResponse(savedClub));
            expect(await save).toEqual(savedClub);
        });

        expectClub(savedClub);
        expect(screen.queryByText(originalClub.name)).not.toBeInTheDocument();
        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(fetchMock).toHaveBeenLastCalledWith('/api/clubs/me', expect.objectContaining({
            method: 'PATCH',
            body: JSON.stringify(requestedChanges),
        }));
    });

    it('conserva el escudo y nombre anteriores si el guardado falla', async () => {
        fetchMock.mockImplementation((url, options) => {
            expect(url).toBe('/api/clubs/me');
            return Promise.resolve(options.method === 'PATCH'
                ? jsonResponse({error: {
                    code: 'CLUB_NAME_DUPLICATE',
                    message: 'Ya existe un club con ese nombre.',
                }}, 409)
                : jsonResponse(originalClub));
        });
        renderNavBar();
        await screen.findByText(originalClub.name);

        await act(async () => {
            await expect(updateMyClub({
                name: 'Nombre duplicado',
                avatar: 'avatar-12.png',
                friendlyAvailable: true,
            })).rejects.toMatchObject({status: 409, code: 'CLUB_NAME_DUPLICATE'});
        });

        expectClub(originalClub);
        expect(screen.queryByText('Nombre duplicado')).not.toBeInTheDocument();
    });

    it.each(['success', 'error'])(
        'mantiene el escudo guardado si la consulta inicial termina después con %s, aunque ignore la cancelación',
        async (outcome) => {
            const initialGet = deferred();
            const savedClub = {...originalClub, name: 'Club actualizado', avatar: 'avatar-15.png'};
            fetchMock.mockImplementation((url, options) => {
                expect(url).toBe('/api/clubs/me');
                // Esta respuesta queda pendiente incluso si se aborta su señal.
                return options.method === 'GET'
                    ? initialGet.promise
                    : Promise.resolve(jsonResponse(savedClub));
            });
            renderNavBar();

            await act(async () => {
                await updateMyClub({
                    name: savedClub.name,
                    avatar: savedClub.avatar,
                    friendlyAvailable: true,
                });
            });
            expectClub(savedClub);

            await act(async () => {
                if (outcome === 'success') {
                    initialGet.resolve(jsonResponse(originalClub));
                } else {
                    initialGet.reject(new Error('La consulta inicial falló tarde.'));
                }
            });

            expectClub(savedClub);
            expect(screen.queryByText(originalClub.name)).not.toBeInTheDocument();
        },
    );

    it('recibe varios guardados consecutivos sin navegar ni recargar', async () => {
        const firstSavedClub = {...originalClub, name: 'Club primero', avatar: 'avatar-04.png'};
        const secondSavedClub = {...originalClub, name: 'Club segundo', avatar: 'avatar-20.png'};
        const savedClubs = [firstSavedClub, secondSavedClub];
        let saveIndex = 0;
        fetchMock.mockImplementation((url, options) => {
            expect(url).toBe('/api/clubs/me');
            return Promise.resolve(jsonResponse(
                options.method === 'PATCH' ? savedClubs[saveIndex++] : originalClub,
            ));
        });
        renderNavBar();
        await screen.findByText(originalClub.name);

        for (const savedClub of savedClubs) {
            await act(async () => {
                await updateMyClub({
                    name: savedClub.name,
                    avatar: savedClub.avatar,
                    friendlyAvailable: true,
                });
            });
            expectClub(savedClub);
        }

        expect(screen.queryByText(firstSavedClub.name)).not.toBeInTheDocument();
        expect(fetchMock).toHaveBeenCalledTimes(3);
    });
});
