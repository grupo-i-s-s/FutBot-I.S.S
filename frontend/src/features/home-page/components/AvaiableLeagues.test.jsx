import {cleanup, render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {afterEach, expect, it, vi} from 'vitest';
import AvaiableLeagues from './AvaiableLeagues';

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

it('muestra solo los accesos a ligas sin consultar el listado', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    render(<MemoryRouter><AvaiableLeagues/></MemoryRouter>);

    expect(screen.getByRole('heading', {name: 'Ligas Disponibles'})).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(3);
    expect(screen.getByRole('link', {name: 'Ver todas las ligas'})).toHaveAttribute('href', '/ligas-disponibles');
    expect(screen.getByRole('link', {name: 'Crear una liga Publica'})).toHaveAttribute('href', '/crear-liga');
    expect(screen.getByRole('link', {name: 'Crear una liga Privada'})).toHaveAttribute('href', '/crear-liga-privada');
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.queryByText('No hay ligas disponibles.')).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
});
