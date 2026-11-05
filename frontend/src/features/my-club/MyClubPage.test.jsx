import {act, cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import MyClubPage from './MyClubPage';
import {useMyClub} from './hooks/useMyClub';
import {getDefaultTeam, getFormations, updateDefaultTeam, updateMyClub} from './api';

vi.mock('./hooks/useMyClub', () => ({useMyClub: vi.fn()}));
vi.mock('./api', () => ({
    getDefaultTeam: vi.fn(), getFormations: vi.fn(),
    updateDefaultTeam: vi.fn(), updateMyClub: vi.fn(),
    assignPlayerBehaviour: vi.fn(),
}));

const club = {id: 7, name: 'Club de prueba', avatar: 'shield', friendlyAvailable: true};
const behaviours = [{id: 10, name: 'Equilibrado'}];
const players = Array.from({length: 6}, (_, index) => ({
    id: index + 1, name: `Jugador ${index + 1}`, behaviorId: 10,
    behaviourName: 'Equilibrado', power: 60, agility: 60,
    control: 60, speed: 60, strength: 60,
}));
let persisted;

async function openSettings() {
    fireEvent.click(screen.getByRole('button', {name: 'Configurar club'}));
    return screen.findByLabelText('Formación');
}

describe('Configuración de formación del club', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        persisted = {
            clubId: 7,
            lineUp: {
                formationId: 1,
                starters: [1, 2, 3].map((playerId) => ({playerId, behaviourId: 10})),
                substitutes: [4, 5, 6].map((playerId) => ({playerId, behaviourId: 10})),
            },
        };
        useMyClub.mockReturnValue({
            status: 'ready', club, players, behaviours, leagues: [],
            reload: vi.fn(), setClub: vi.fn(), updatePlayer: vi.fn(),
        });
        getDefaultTeam.mockImplementation(async () => structuredClone(persisted));
        getFormations.mockResolvedValue({
            items: ['2-1', '1-2', '1-1-1'].map((name, index) => ({
                id: index + 1, name, description: `Distribución ${name}`,
                slots: ['Atrás', 'Medio', 'Adelante'].map((label) => ({label})),
            })),
        });
        updateDefaultTeam.mockImplementation(async (lineUp) => {
            persisted = {clubId: 7, lineUp: structuredClone(lineUp)};
            return structuredClone(persisted);
        });
    });

    afterEach(cleanup);

    it('selecciona y guarda desde el diálogo y recupera lo guardado al abrirlo otra vez', async () => {
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        expect(screen.queryByLabelText('Formación')).not.toBeInTheDocument();
        expect(getDefaultTeam).not.toHaveBeenCalled();

        const select = await openSettings();
        expect(select).toHaveValue('1');
        expect(screen.getAllByRole('option', {name: /^(2-1|1-2|1-1-1)$/})).toHaveLength(3);
        expect(document.querySelector('form form')).toBeNull();
        expect(document.querySelector('canvas')).toBeNull();
        expect(document.querySelector('svg[aria-label^="Distribución"]')).toBeNull();
        const original = structuredClone(persisted.lineUp);

        fireEvent.change(select, {target: {value: '2'}});
        fireEvent.click(screen.getByRole('button', {name: 'Guardar equipo'}));
        expect(await screen.findByText('Equipo guardado correctamente.')).toBeInTheDocument();
        expect(updateDefaultTeam).toHaveBeenCalledWith({...original, formationId: 2});
        expect(updateMyClub).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', {name: 'Cancelar'}));
        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
        expect(await openSettings()).toHaveValue('2');
    });

    it('conserva la selección si falla el guardado y muestra el error', async () => {
        updateDefaultTeam.mockRejectedValue(new Error('No se pudo guardar la formación.'));
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const select = await openSettings();
        fireEvent.change(select, {target: {value: '3'}});
        fireEvent.click(screen.getByRole('button', {name: 'Guardar equipo'}));

        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar la formación.');
        expect(select).toHaveValue('3');
        expect(persisted.lineUp.formationId).toBe(1);
        expect(screen.getByRole('button', {name: 'Guardar equipo'})).toBeEnabled();
    });

    it('espera el guardado antes de permitir cerrar o guardar los datos del club', async () => {
        let finishSave;
        updateDefaultTeam.mockImplementation(() => new Promise((resolve) => {finishSave = resolve;}));
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const select = await openSettings();
        fireEvent.click(screen.getByRole('button', {name: 'Guardar equipo'}));

        expect(select).toBeDisabled();
        expect(screen.getByRole('button', {name: 'Cancelar'})).toBeDisabled();
        expect(screen.getByRole('button', {name: 'Guardando…'})).toBeDisabled();
        expect(screen.queryByRole('button', {name: 'Close'})).not.toBeInTheDocument();
        fireEvent.keyDown(screen.getByRole('dialog'), {key: 'Escape'});
        expect(screen.getByRole('dialog')).toBeInTheDocument();

        await act(async () => finishSave(structuredClone(persisted)));
        expect(await screen.findByText('Equipo guardado correctamente.')).toBeInTheDocument();
        expect(screen.getByRole('button', {name: 'Cancelar'})).toBeEnabled();
    });
});
