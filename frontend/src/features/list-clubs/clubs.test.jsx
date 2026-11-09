import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
} from '@testing-library/react';
import {Link, MemoryRouter} from 'react-router';
import {
    afterEach,
    beforeEach,
    expect,
    it,
    vi,
} from 'vitest';

import App from '../../App.jsx';
import {request} from '../../api/http.js';

vi.mock('../../api/http.js', async (importOriginal) => ({
    ...await importOriginal(),
    request: vi.fn(),
}));

vi.mock('../my-club/api.js', async (importOriginal) => ({
    ...await importOriginal(),
    getMyClub: async () => ({id: 8, name: 'Mi club', avatar: 'avatar-01.png'}),
}));

vi.mock('../nav-bar/navBar.jsx', () => ({
    default: () => null,
}));

function club(id, name) {
    return {id, name, avatar: 'avatar-01.png'};
}

function listing(
    items,
    {page = 1, total = items.length, hasNext = false} = {},
) {
    return {
        items,
        page,
        pageSize: 20,
        total,
        hasNext,
    };
}

function profile(id, name) {
    return {
        ...club(id, name),
        stats: {
            played: 0,
            wins: 0,
            draws: 0,
            losses: 0,
        },
        ranking: {
            position: id,
            points: 0,
            source: 'PUBLIC_LEAGUES',
        },
        players: [
            {id: id * 10, name: `Jugador de ${name}`},
        ],
    };
}

function deferred() {
    let resolve;

    const promise = new Promise((finish) => {
        resolve = finish;
    });

    return {promise, resolve};
}

async function open(path = '/clubes') {
    await act(async () => {
        render(
            <MemoryRouter initialEntries={[path]}>
                <Link to="/clubes/2">Otro club</Link>
                <App/>
            </MemoryRouter>,
        );
    });
}

async function advance(milliseconds = 300) {
    await act(async () => {
        await vi.advanceTimersByTimeAsync(milliseconds);
    });
}

async function click(name) {
    await act(async () => {
        fireEvent.click(screen.getByRole('button', {name}));
    });
}

function lastQuery() {
    const [path] = request.mock.calls.at(-1);
    return new URL(path, 'http://test').searchParams;
}

beforeEach(() => {
    request.mockReset();
    vi.useFakeTimers();
});

afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
});

it('espera 300 ms y envía el nombre sin espacios exteriores', async () => {
    request.mockResolvedValue(listing([club(1, 'River')]));

    await open();

    expect(request).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('img', {
        name: 'Escudo de River',
    })).toBeInTheDocument();

    fireEvent.change(screen.getByRole('searchbox'), {
        target: {value: 'ri'},
    });

    await advance(100);

    fireEvent.change(screen.getByRole('searchbox'), {
        target: {value: '  river  '},
    });

    await advance(299);
    expect(request).toHaveBeenCalledTimes(1);

    await advance(1);

    expect(request).toHaveBeenCalledTimes(2);
    expect(lastQuery().get('name')).toBe('river');
    expect(lastQuery().get('page')).toBe('1');
    expect(lastQuery().get('pageSize')).toBe('20');
});

it('reinicia la página al filtrar y restaura el listado al limpiar', async () => {
    request.mockImplementation(async (path) => {
        const params = new URL(path, 'http://test').searchParams;
        const page = Number(params.get('page'));

        if (params.get('name')) {
            return listing([]);
        }

        return listing([club(page, `Club página ${page}`)], {
            page,
            total: 21,
            hasNext: page === 1,
        });
    });

    await open();
    await click('Siguiente');

    expect(lastQuery().get('page')).toBe('2');

    fireEvent.change(screen.getByRole('searchbox'), {
        target: {value: 'inexistente'},
    });
    await advance();

    expect(lastQuery().get('page')).toBe('1');
    expect(screen.getByText(
        'No se encontraron clubes con el nombre "inexistente".',
    )).toBeInTheDocument();

    fireEvent.change(screen.getByRole('searchbox'), {
        target: {value: ''},
    });
    await advance();

    expect(lastQuery().get('name')).toBeNull();
    expect(lastQuery().get('page')).toBe('1');
    expect(screen.getByText('Club página 1')).toBeInTheDocument();
});

it('ignora una respuesta vieja de la búsqueda', async () => {
    const oldResponse = deferred();
    let oldSignal;

    request.mockImplementation((path, options) => {
        const name = new URL(path, 'http://test').searchParams.get('name');

        if (name === 'viejo') {
            oldSignal = options.signal;
            return oldResponse.promise;
        }

        return Promise.resolve(listing([club(2, 'Resultado nuevo')]));
    });

    await open();

    fireEvent.change(screen.getByRole('searchbox'), {
        target: {value: 'viejo'},
    });
    await advance();

    fireEvent.change(screen.getByRole('searchbox'), {
        target: {value: 'nuevo'},
    });

    expect(oldSignal.aborted).toBe(true);
    await advance();

    await act(async () => {
        oldResponse.resolve(listing([club(1, 'Resultado viejo')]));
    });

    expect(screen.getByText('Resultado nuevo')).toBeInTheDocument();
    expect(screen.queryByText('Resultado viejo')).not.toBeInTheDocument();
});

it('abre el perfil elegido desde el listado', async () => {
    request.mockImplementation(async (path) => {
        if (path.startsWith('/clubs?')) {
            return listing([club(1, 'River')]);
        }

        return profile(1, 'River');
    });

    await open();

    await act(async () => {
        fireEvent.click(screen.getByRole('link', {
            name: 'Ver perfil de River',
        }));
    });

    expect(request).toHaveBeenLastCalledWith(
        '/clubs/1',
        expect.objectContaining({signal: expect.anything()}),
    );
    expect(screen.getByRole('heading', {
        level: 1,
        name: 'River',
    })).toBeInTheDocument();
    expect(screen.getByText('Jugador de River')).toBeInTheDocument();
});

it('muestra ceros y ranking inicial sin controles de edición', async () => {
    request.mockResolvedValue(profile(1, 'Club nuevo'));

    await open('/clubes/1');

    for (const label of [
        'Partidos jugados',
        'Victorias',
        'Empates',
        'Derrotas',
        'Puntos',
    ]) {
        expect(screen.getByText(label).nextElementSibling)
            .toHaveTextContent('0');
    }

    expect(screen.getByText('Posición').nextElementSibling)
        .toHaveTextContent('1');

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
});

it('limpia el perfil anterior mientras carga otro club', async () => {
    const second = deferred();

    request
        .mockResolvedValueOnce(profile(1, 'Primero'))
        .mockReturnValueOnce(second.promise);

    await open('/clubes/1');

    await act(async () => {
        fireEvent.click(screen.getByRole('link', {name: 'Otro club'}));
    });

    expect(screen.getByRole('status')).toHaveTextContent('Cargando club');
    expect(screen.queryByRole('heading', {
        name: 'Primero',
    })).not.toBeInTheDocument();

    await act(async () => {
        second.resolve(profile(2, 'Segundo'));
    });

    expect(screen.getByRole('heading', {
        name: 'Segundo',
    })).toBeInTheDocument();
});

it('ignora un perfil anterior que termina de cargar más tarde', async () => {
    const first = deferred();

    request.mockImplementation((path) => (
        path === '/clubs/1'
            ? first.promise
            : Promise.resolve(profile(2, 'Segundo'))
    ));

    await open('/clubes/1');

    await act(async () => {
        fireEvent.click(screen.getByRole('link', {name: 'Otro club'}));
    });

    await act(async () => {
        first.resolve(profile(1, 'Primero'));
    });

    expect(screen.getByRole('heading', {
        name: 'Segundo',
    })).toBeInTheDocument();

    expect(screen.queryByRole('heading', {
        name: 'Primero',
    })).not.toBeInTheDocument();
});

it.each([
    [404, 'Club no encontrado'],
    [0, 'No se pudo conectar con el servidor.'],
    [401, 'Iniciá sesión para consultar este club.'],
])('distingue el error de perfil con estado %s', async (status, message) => {
    request.mockRejectedValue({status});

    await open('/clubes/1');

    expect(screen.getByRole('alert')).toHaveTextContent(message);

    if (status === 404) {
        expect(screen.queryByRole('button', {
            name: 'Reintentar',
        })).not.toBeInTheDocument();
    }

    if (status === 401) {
        expect(screen.getByRole('link', {
            name: 'Iniciar sesión',
        })).toHaveAttribute('href', '/iniciar-sesion');
    }
});

it('permite reintentar la carga del perfil', async () => {
    request
        .mockRejectedValueOnce({status: 0})
        .mockResolvedValueOnce(profile(1, 'Recuperado'));

    await open('/clubes/1');
    await click('Reintentar');

    expect(screen.getByRole('heading', {
        name: 'Recuperado',
    })).toBeInTheDocument();
});
