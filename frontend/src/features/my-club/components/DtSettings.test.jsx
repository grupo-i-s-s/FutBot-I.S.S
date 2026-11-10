import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import DtSettings from './DtSettings';

const strategies = [{id: 10, name: 'Cuidar el resultado'}, {id: 11, name: 'Remontada'}];
const reply = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function renderSettings(dt, onSaveSuccess) {
    return render(<MemoryRouter><DtSettings dt={dt} onSaveSuccess={onSaveSuccess} /></MemoryRouter>);
}

it('recupera y guarda la activación y la estrategia en el endpoint del DT', async () => {
    let saved = {id: 1, isActive: false, activeBehaviourId: 10};
    const fetchMock = vi.fn(async (url, options) => {
        if (url === '/api/clubs/me/dt/behaviours') return reply({items: strategies});
        expect(url).toBe('/api/clubs/me/dt');
        expect(options.method).toBe('PATCH');
        expect(options.headers['X-FutBot-Request']).toBe('1');
        saved = {...saved, ...JSON.parse(options.body)};
        return reply(saved);
    });
    vi.stubGlobal('fetch', fetchMock);
    const onSaveSuccess = vi.fn();
    const view = renderSettings(saved, onSaveSuccess);
    const select = await screen.findByLabelText('Comportamiento del DT');
    const activation = screen.getByRole('switch', {name: 'Activar DT para próximos partidos'});
    expect(select).toHaveValue('10');
    expect(activation).not.toBeChecked();

    fireEvent.change(select, {target: {value: '11'}});
    fireEvent.click(activation);
    fireEvent.click(screen.getByRole('button', {name: 'Guardar DT'}));
    await waitFor(() => expect(onSaveSuccess).toHaveBeenCalledWith('Configuración del DT guardada.'));
    expect(saved).toEqual({id: 1, isActive: true, activeBehaviourId: 11});
    expect(screen.getByRole('link', {name: 'Crear comportamiento del DT'})).toHaveAttribute('href', '/crear-comportamiento-dt');

    view.unmount();
    renderSettings(saved);
    expect(await screen.findByLabelText('Comportamiento del DT')).toHaveValue('11');
    expect(screen.getByRole('switch')).toBeChecked();
});

it('exige una estrategia para activar el DT y conserva la selección si falla el guardado', async () => {
    const fetchMock = vi.fn(async (url) => url === '/api/clubs/me/dt/behaviours'
        ? reply({items: strategies})
        : reply({error: {message: 'No se pudo guardar el cambio.'}}, 409));
    vi.stubGlobal('fetch', fetchMock);
    renderSettings(null);
    const select = await screen.findByLabelText('Comportamiento del DT');
    fireEvent.click(screen.getByRole('switch'));
    expect(screen.getByRole('button', {name: 'Guardar DT'})).toBeDisabled();

    fireEvent.change(select, {target: {value: '10'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar DT'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar el cambio.');
    expect(select).toHaveValue('10');
    expect(screen.getByRole('switch')).toBeChecked();
});
