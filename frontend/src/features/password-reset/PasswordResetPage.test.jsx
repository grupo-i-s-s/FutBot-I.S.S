import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import App from '../../App.jsx';

let fetchMock;
let sessionResponse;

beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(
        new Response('{}', {status: 202}),
    );
    sessionResponse = new Response(JSON.stringify({
        error: {code: 'SESSION_INVALID', message: 'La sesión venció.'},
    }), {status: 401});
    vi.stubGlobal('fetch', (url, options) => {
        if (url === '/api/clubs/me') {
            return Promise.resolve(sessionResponse.clone());
        }
        return fetchMock(url, options);
    });
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.unstubAllGlobals();
});

function openPage(path = '/recuperar-contrasena') {
    render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
}

function fill(label, value) {
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
}

function submit() {
    fireEvent.submit(screen.getByLabelText('Email').closest('form'));
}

async function requestCode() {
    openPage();
    fill('Email', 'user@example.com');
    submit();
    await screen.findByLabelText('Código de recuperación');
}

function fillConfirmation(password = 'nueva-clave', confirmation = password) {
    fill('Código de recuperación', '004281');
    fill('Nueva contraseña', password);
    fill('Repetir nueva contraseña', confirmation);
}

async function advanceSeconds(seconds) {
    for (let i = 0; i < seconds; i++) {
        await act(async () => vi.advanceTimersByTime(1000));
    }
}

it('permite entrar desde login y volver', async () => {
    openPage('/login');
    fireEvent.click(await screen.findByRole('link', {name: 'Olvidé mi contraseña'}));
    expect(screen.getByText('Recuperar contraseña')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', {name: 'Volver al login'}));
    expect(screen.getByRole('button', {name: 'Iniciar Sesión'})).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
});

it('no envía un email inválido', async () => {
    await act(async () => openPage());
    fill('Email', 'correo-invalido');
    submit();

    expect(screen.getByLabelText('Email')).toBeInvalid();
    expect(fetchMock).not.toHaveBeenCalled();
});

it('evita duplicados y después del 202 conserva el email y muestra mensaje genérico', async () => {
    let finish;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => {
        finish = resolve;
    }));

    await act(async () => openPage());
    fill('Email', 'user@example.com');
    submit();
    submit();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', {name: 'Procesando...'})).toBeDisabled();

    await act(async () => finish(new Response('{}', {status: 202})));

    expect(screen.getByLabelText('Email')).toHaveValue('user@example.com');
    expect(screen.getByText(/Si la cuenta existe/)).toBeInTheDocument();

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/auth/password-reset/request');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({email: 'user@example.com'});
});

it('permite reenviar recién después de 60 segundos', async () => {
    vi.useFakeTimers();
    openPage();
    fill('Email', 'user@example.com');
    await act(async () => submit());

    const resend = screen.getByRole('button', {name: 'Reenviar código'});
    expect(resend).toBeDisabled();
    fireEvent.click(resend);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await advanceSeconds(60);
    expect(resend).toBeEnabled();

    await act(async () => fireEvent.click(resend));
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/auth/password-reset/request');
    expect(resend).toBeDisabled();
});

it('respeta Retry-After cuando el servidor responde 429', async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
        error: {
            code: 'PASSWORD_RESET_RATE_LIMIT',
            message: 'Esperá antes de solicitar otro código.',
        },
    }), {status: 429, headers: {'Retry-After': '2'}}));

    openPage();
    fill('Email', 'user@example.com');
    await act(async () => submit());
    expect(screen.getByRole('alert')).toHaveTextContent('Esperá');

    const button = screen.getByRole('button', {name: 'Solicitar código'});
    expect(button).toBeDisabled();

    await advanceSeconds(1);
    expect(button).toBeDisabled();

    await advanceSeconds(1);
    expect(button).toBeEnabled();
});

it('muestra el error de red y permite volver a intentar', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    openPage();
    fill('Email', 'user@example.com');
    submit();

    expect(await screen.findByRole('alert')).toHaveTextContent(
        'No se pudo conectar con el servidor.',
    );
    expect(screen.getByRole('button', {name: 'Solicitar código'})).toBeEnabled();
    expect(screen.queryByLabelText('Código de recuperación')).not.toBeInTheDocument();
});

it('no confirma si las contraseñas son distintas', async () => {
    await requestCode();
    fillConfirmation('nueva-clave', 'otra-clave');
    submit();

    expect(screen.getByRole('alert')).toHaveTextContent('Las contraseñas no coinciden');
    expect(screen.getByLabelText('Repetir nueva contraseña')).toBeInvalid();
    expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('no envía la confirmación cuando el navegador rechaza el formato', async () => {
    await requestCode();
    fillConfirmation();

    const form = screen.getByLabelText('Email').closest('form');
    vi.spyOn(form, 'reportValidity').mockReturnValue(false);
    submit();

    expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('rechaza un código incorrecto sin mostrar éxito y mantiene el reenvío', async () => {
    await requestCode();
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
        error: {
            code: 'PASSWORD_RESET_INVALID',
            message: 'El código no es válido o venció.',
        },
    }), {status: 400}));

    fillConfirmation();
    submit();

    expect(await screen.findByRole('alert')).toHaveTextContent('El código no es válido');
    expect(screen.queryByText(/Contraseña actualizada/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Reenviar código'})).toBeInTheDocument();
});

it.each([false, true])('conserva el cero del código y tras el 204 limpia el formulario y ofrece login (sesión activa: %s)', async (authenticated) => {
    if (authenticated) {
        sessionResponse = new Response(JSON.stringify({id: 8, name: 'Club de pruebas', avatar: 'avatar-01.png'}));
    }
    await requestCode();
    if (authenticated) await screen.findByRole('button', {name: 'Cerrar sesión'});
    fetchMock.mockResolvedValueOnce(new Response(null, {status: 204}));

    fillConfirmation();
    submit();

    expect(await screen.findByText(/Contraseña actualizada/)).toBeInTheDocument();

    const [url, options] = fetchMock.mock.calls[1];
    expect(url).toBe('/api/auth/password-reset/confirm');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
        email: 'user@example.com',
        code: '004281',
        newPassword: 'nueva-clave',
        passwordConfirmation: 'nueva-clave',
    });
    expect(document.querySelector('input')).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('button', {name: 'Cerrar sesión'})).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', {name: 'Volver al login'}));
    fireEvent.click(screen.getByRole('link', {name: 'Olvidé mi contraseña'}));
    expect(screen.getByLabelText('Email')).toHaveValue('');
});
