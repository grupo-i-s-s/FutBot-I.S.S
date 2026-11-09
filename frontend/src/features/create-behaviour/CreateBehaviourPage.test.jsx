import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import CreateBehaviourPage from './CreateBehaviourPage';

vi.mock('@monaco-editor/react', () => ({
    default: ({defaultValue, onChange, options}) => (
        <textarea aria-label={options.ariaLabel} defaultValue={defaultValue}
                  readOnly={options.readOnly} onChange={event => onChange(event.target.value)} />
    ),
}));

const reply = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function Destination() {
    const location = useLocation();
    return <p data-tab={location.state?.tab}>{location.state?.notice ?? 'Catálogo de jugadores'}</p>;
}

function renderEditor(kind) {
    render(<MemoryRouter initialEntries={['/editor']}>
        <Routes>
            <Route path="/editor" element={<CreateBehaviourPage kind={kind} />} />
            <Route path="/mi-club" element={<Destination />} />
            <Route path="/comportamientos" element={<Destination />} />
        </Routes>
    </MemoryRouter>);
}

it('valida la plantilla del DT y guarda el comportamiento en su catálogo', async () => {
    const fetchMock = vi.fn(async (url) => url === '/api/behaviours/validate'
        ? reply({valid: true, diagnostics: []})
        : reply({id: 12}, 201));
    vi.stubGlobal('fetch', fetchMock);
    renderEditor('DT');
    const code = screen.getByLabelText('Código del comportamiento').value;
    expect(code).toContain('cambiar_comportamiento');
    expect(code).toContain('sustituir');
    fireEvent.click(screen.getByRole('button', {name: 'Validar código'}));
    expect(await screen.findByText('El código es válido.')).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/behaviours/validate');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({kind: 'COACH', code});

    fireEvent.change(screen.getByLabelText('Nombre del comportamiento'), {target: {value: 'Mi táctica'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar Comportamiento'}));
    expect(await screen.findByText(/Comportamiento del DT creado/)).toHaveAttribute('data-tab', 'dt');
    expect(fetchMock.mock.calls[1][0]).toBe('/api/clubs/me/dt/behaviours');
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({name: 'Mi táctica', code});
});

it('muestra el diagnóstico del servidor sin perder el código editado', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply({
        error: {
            message: 'El programa del DT es inválido.',
            diagnostics: [{line: 3, column: 1, code: 'INVALID_ACTION', message: 'Revisá las órdenes.'}],
        },
    }, 400)));
    renderEditor('DT');
    const editor = screen.getByLabelText('Código del comportamiento');
    fireEvent.change(editor, {target: {value: 'Mi código'}});
    fireEvent.change(screen.getByLabelText('Nombre del comportamiento'), {target: {value: 'Mi táctica'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar Comportamiento'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Línea 3 · Revisá las órdenes.');
    expect(editor).toHaveValue('Mi código');
});

it('conserva el catálogo y la ruta de guardado de los comportamientos de jugadores', async () => {
    const fetchMock = vi.fn(async () => reply({id: 12}, 201));
    vi.stubGlobal('fetch', fetchMock);
    renderEditor();
    const code = 'def decide(obs):\n    return ir_a_pelota()';
    fireEvent.change(screen.getByLabelText('Código del comportamiento'), {target: {value: code}});
    fireEvent.change(screen.getByLabelText('Nombre del comportamiento'), {target: {value: 'Mi jugador'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar Comportamiento'}));
    expect(await screen.findByText('Catálogo de jugadores')).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/behaviours');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({name: 'Mi jugador', code, kind: 'PLAYER'});
});
