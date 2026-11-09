import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router';
import {routes} from '@/routes.js';
import RegisterPage from './RegisterPage.jsx';
import VerifyEmailPage from './VerifyEmailPage.jsx';

const email = 'club@example.com';

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function jsonResponse(body, status = 200) {
    return {ok: status < 400, status, json: async () => body};
}

function renderRegistration(initialEntry, respond) {
    const request = vi.fn(async (url, {body}) => respond(url, JSON.parse(body)));
    vi.stubGlobal('fetch', request);
    render(
        <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
                <Route path={routes.register} element={<RegisterPage/>}/>
                <Route path={routes.verifyEmail} element={<VerifyEmailPage/>}/>
            </Routes>
        </MemoryRouter>,
    );
    return request;
}

function change(label, value) {
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
}

it('muestra el alta pendiente y permite continuar con los datos anteriores de forma explícita', async () => {
    const request = renderRegistration(routes.register, (url, body) => {
        if (url === '/api/auth/register') {
            return jsonResponse({error: {code: 'EMAIL_VERIFICATION_PENDING', message: 'Ya hay una verificación pendiente.'}}, 409);
        }
        expect(url).toBe('/api/auth/verify-email');
        expect(body).toEqual({email, code: '123456'});
        return jsonResponse({clubId: 1, email});
    });
    change('Nombre del Club', 'Nombre modificado');
    change('Email', email);
    change('Contraseña', 'replacement-password');
    change('Confirmar Contraseña', 'replacement-password');
    fireEvent.click(screen.getByRole('button', {name: 'Registrar Club'}));

    expect(await screen.findByRole('alert')).toHaveTextContent('Ya hay una verificación pendiente.');
    expect(screen.getByLabelText('Nombre del Club')).toHaveValue('Nombre modificado');
    expect(screen.getByRole('link', {name: 'Cambiar los datos con el código'})).toBeInTheDocument();
    expect(request).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('link', {name: 'Continuar con los datos anteriores'}));
    change('Código de verificación', '123456');
    fireEvent.click(screen.getByRole('button', {name: 'Verificar correo'}));
    expect(await screen.findByText('¡Correo verificado! Ya podés iniciar sesión.')).toBeInTheDocument();
});

it('permite corregir un nombre ocupado con el mismo código sin pedir una contraseña nueva', async () => {
    const attempts = [];
    renderRegistration({pathname: routes.verifyEmail, state: {email}}, (url, body) => {
        expect(url).toBe('/api/auth/verify-email');
        attempts.push(body);
        if (attempts.length === 1) {
            return jsonResponse({error: {
                code: 'ACCOUNT_DUPLICATE',
                message: 'Ya existe un club con ese nombre.',
                fields: {clubName: 'Ya existe un club con ese nombre.'},
            }}, 400);
        }
        return jsonResponse({clubId: 1, email});
    });
    change('Código de verificación', '123456');
    fireEvent.click(screen.getByRole('button', {name: 'Verificar correo'}));

    expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe un club con ese nombre.');
    expect(screen.getByLabelText('Código de verificación')).toHaveValue('123456');
    change('Nuevo nombre del club', 'Nombre libre');
    fireEvent.click(screen.getByRole('button', {name: 'Verificar correo'}));

    expect(await screen.findByText('¡Correo verificado! Ya podés iniciar sesión.')).toBeInTheDocument();
    expect(attempts).toEqual([
        {email, code: '123456'},
        {email, code: '123456', registration: {clubName: 'Nombre libre'}},
    ]);
});
