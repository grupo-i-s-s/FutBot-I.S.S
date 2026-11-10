import {act, cleanup, fireEvent, render, screen, within} from '@testing-library/react';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import {toast} from 'sonner';
import {Toaster} from '@/components/ui/sonner';
import CreateBehaviourDialog from './CreateBehaviourDialog';
import CreateBehaviourPage from './CreateBehaviourPage';

vi.mock('@monaco-editor/react', () => ({
    default: ({value, onChange, options}) => (
        <textarea aria-label={options.ariaLabel} value={value}
                  readOnly={options.readOnly} onChange={event => onChange(event.target.value)} />
    ),
}));

const reply = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

afterEach(() => {
    cleanup();
    toast.dismiss();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

function Destination() {
    const location = useLocation();
    return <p data-tab={location.state?.tab}>{location.state?.notice ?? 'Catálogo de jugadores'}</p>;
}

function renderDtEditor() {
    const router = createMemoryRouter([
        {path: '/editor', element: <CreateBehaviourPage/>},
        {path: '/mi-club', element: <Destination/>},
    ], {initialEntries: ['/editor']});
    render(<RouterProvider router={router}/>);
}

it('valida la plantilla del DT y guarda el comportamiento en su catálogo', async () => {
    const fetchMock = vi.fn(async (url) => url === '/api/behaviours/validate'
        ? reply({valid: true, diagnostics: []})
        : reply({id: 12}, 201));
    vi.stubGlobal('fetch', fetchMock);
    renderDtEditor();
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
    renderDtEditor();
    const editor = screen.getByLabelText('Código del comportamiento');
    fireEvent.change(editor, {target: {value: 'Mi código'}});
    fireEvent.change(screen.getByLabelText('Nombre del comportamiento'), {target: {value: 'Mi táctica'}});
    fireEvent.click(screen.getByRole('button', {name: 'Guardar Comportamiento'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('El programa del DT es inválido.');
    expect(screen.getByRole('list', {name: 'Diagnósticos del código'})).toHaveTextContent('Línea 3, columna 1: Revisá las órdenes.');
    expect(editor).toHaveValue('Mi código');
});

it('conserva el borrador del DT al cancelar el cierre y vuelve a su pestaña al confirmar', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderDtEditor();
    const dialog = screen.getByRole('dialog', {name: 'Crear comportamiento del DT'});
    fireEvent.change(screen.getByLabelText('Nombre del comportamiento'), {target: {value: 'Borrador del DT'}});

    fireEvent.click(within(dialog).getByRole('button', {name: 'Cancelar'}));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Nombre del comportamiento')).toHaveValue('Borrador del DT');

    confirm.mockReturnValue(true);
    fireEvent.click(within(dialog).getByRole('button', {name: 'Cancelar'}));
    expect(await screen.findByText('Catálogo de jugadores')).toHaveAttribute('data-tab', 'dt');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

function renderDialog(onCreated) {
    const router = createMemoryRouter([
        {path: '/mi-club', element: <CreateBehaviourDialog onCreated={onCreated}/>},
    ], {initialEntries: ['/mi-club']});
    render(<>
        <RouterProvider router={router}/>
        <Toaster containerAriaLabel="Notificaciones"/>
    </>);
}

function openDialog() {
    fireEvent.click(screen.getByRole('button', {name: 'Crear nuevo comportamiento'}));
    return screen.getByRole('dialog', {name: 'Crear comportamiento'});
}

it('valida y guarda un comportamiento de jugador una sola vez desde el diálogo', async () => {
    const response = Promise.withResolvers();
    const onCreated = vi.fn();
    const saved = {id: 12, name: 'Mi jugador', description: '', kind: 'PLAYER', version: 1, validationStatus: 'VALID'};
    const fetchMock = vi.fn(async url => url === '/api/behaviours/validate'
        ? reply({valid: true, diagnostics: []})
        : response.promise);
    vi.stubGlobal('fetch', fetchMock);
    renderDialog(onCreated);
    const dialog = openDialog();
    const view = within(dialog);
    const code = 'def decide(obs):\n    return ir_a_pelota()';
    const name = view.getByLabelText('Nombre del comportamiento');
    fireEvent.change(view.getByLabelText('Código del comportamiento'), {target: {value: code}});
    fireEvent.change(name, {target: {value: ' Mi jugador '}});
    fireEvent.click(view.getByRole('button', {name: 'Validar código'}));
    expect(await view.findByText('El código es válido.')).toBeVisible();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/behaviours/validate');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({kind: 'PLAYER', code});

    fireEvent.click(view.getByRole('button', {name: 'Guardar comportamiento'}));
    fireEvent.submit(name.form);
    fireEvent.keyDown(dialog, {key: 'Escape'});
    expect(dialog).toBeVisible();
    expect(view.getByRole('button', {name: 'Cancelar'})).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/behaviours');
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({name: saved.name, code, kind: 'PLAYER'});

    await act(async () => response.resolve(reply(saved, 201)));
    expect(onCreated).toHaveBeenCalledExactlyOnceWith(saved);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    const reopened = within(openDialog());
    expect(reopened.getByLabelText('Nombre del comportamiento')).toHaveValue('');
    expect(reopened.getByLabelText('Código del comportamiento')).toHaveValue('def decide(observation):\n    return ir_a_pelota()\n');
});

it('informa errores del servidor y pide confirmar antes de descartar el borrador', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply({
        error: {
            message: 'El código es inválido.',
            diagnostics: [{line: 2, column: 1, code: 'INVALID_ACTION', message: 'Revisá la acción.'}],
        },
    }, 400)));
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
    const onCreated = vi.fn();
    renderDialog(onCreated);
    const dialog = openDialog();
    const view = within(dialog);
    const editor = view.getByLabelText('Código del comportamiento');
    fireEvent.change(view.getByLabelText('Nombre del comportamiento'), {target: {value: 'Mi jugador'}});
    fireEvent.change(editor, {target: {value: 'Mi código'}});
    fireEvent.click(view.getByRole('button', {name: 'Guardar comportamiento'}));

    expect(await view.findByRole('alert')).toHaveTextContent('El código es inválido.');
    expect(view.getByRole('list', {name: 'Diagnósticos del código'})).toHaveTextContent('Línea 2, columna 1: Revisá la acción.');
    const notifications = within(screen.getByRole('region', {name: /^Notificaciones/}));
    expect(await notifications.findByText('No se pudo crear el comportamiento')).toBeVisible();
    expect(onCreated).not.toHaveBeenCalled();

    fireEvent.click(view.getByRole('button', {name: 'Cancelar'}));
    expect(dialog).toBeVisible();
    expect(editor).toHaveValue('Mi código');
    fireEvent.click(view.getByRole('button', {name: 'Cancelar'}));
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
