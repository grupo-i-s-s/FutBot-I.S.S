import {act, cleanup, fireEvent, render, screen, within} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import MyClubPage from './MyClubPage';
import {
    getDefaultTeam, getFormations, getMyClub, getPlayersByIds, listBehaviours, listMyLeagues,
    listPlayers, updateDefaultTeam, updateMyClub,
} from './api';

vi.mock('./api', () => ({
    getDefaultTeam: vi.fn(), getFormations: vi.fn(),
    updateDefaultTeam: vi.fn(), updateMyClub: vi.fn(),
    assignPlayerBehaviour: vi.fn(), getMyClub: vi.fn(), getPlayersByIds: vi.fn(),
    listBehaviours: vi.fn(), listMyLeagues: vi.fn(), listPlayers: vi.fn(),
}));

const club = {id: 7, name: 'Club de prueba', avatar: 'shield', friendlyAvailable: true};
const behaviours = [{id: 10, name: 'Equilibrado'}, {id: 11, name: 'Ofensivo'}];
const players = Array.from({length: 12}, (_, index) => ({
    id: index + 1, name: `Jugador ${index + 1}`, behaviorId: 10,
    behaviourName: 'Equilibrado', power: 60, agility: 60,
    control: 60, speed: 60, strength: 60,
}));
let persisted;

function rosterPage({page, limit, search}) {
    const matching = search ? players.filter(player => player.name.includes(search)) : players;
    return {
        items: matching.slice((page - 1) * limit, page * limit),
        total: matching.length,
        totalPages: Math.ceil(matching.length / limit),
    };
}

async function openSettings() {
    fireEvent.click(await screen.findByRole('button', {name: 'Configurar club'}));
    return within(await screen.findByRole('dialog'));
}

async function teamEditor() {
    return within(await screen.findByRole('complementary', {name: 'Mi equipo'}));
}

describe('Configuración de formación del club', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        persisted = {
            clubId: 7,
            lineUp: {
                formationId: 1,
                starters: [10, 2, 3].map((playerId) => ({playerId, behaviourId: 10})),
                substitutes: [4, 5, 6].map((playerId) => ({playerId, behaviourId: 10})),
            },
        };
        getMyClub.mockResolvedValue(club);
        listBehaviours.mockResolvedValue({items: behaviours});
        listMyLeagues.mockResolvedValue({items: []});
        listPlayers.mockImplementation(async params => rosterPage(params));
        getPlayersByIds.mockImplementation(async ids => players.filter(player => ids.includes(player.id)));
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

    it('selecciona y guarda desde Mi equipo y recupera lo guardado al volver a entrar', async () => {
        const {unmount} = render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const select = await editor.findByLabelText('Formación');
        expect(select).toHaveValue('1');
        expect(editor.getAllByRole('option', {name: /^(2-1|1-2|1-1-1)$/})).toHaveLength(3);
        expect(document.querySelector('form form')).toBeNull();
        expect(document.querySelector('canvas')).toBeNull();
        expect(document.querySelector('svg[aria-label^="Distribución"]')).toBeNull();
        const original = structuredClone(persisted.lineUp);

        fireEvent.change(select, {target: {value: '2'}});
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));
        expect(await editor.findByText('Equipo guardado correctamente.')).toBeInTheDocument();
        expect(updateDefaultTeam).toHaveBeenCalledWith({...original, formationId: 2});
        expect(updateMyClub).not.toHaveBeenCalled();

        unmount();
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        expect(await (await teamEditor()).findByLabelText('Formación')).toHaveValue('2');
    });

    it('conserva la selección si falla el guardado y muestra el error', async () => {
        updateDefaultTeam.mockRejectedValue(new Error('No se pudo guardar la formación.'));
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const select = await editor.findByLabelText('Formación');
        fireEvent.change(select, {target: {value: '3'}});
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));

        expect(await editor.findByRole('alert')).toHaveTextContent('No se pudo guardar la formación.');
        expect(select).toHaveValue('3');
        expect(persisted.lineUp.formationId).toBe(1);
        expect(editor.getByRole('button', {name: 'Guardar equipo'})).toBeEnabled();
    });

    it('espera el guardado antes de permitir cerrar o guardar los datos del club', async () => {
        let finishSave;
        updateDefaultTeam.mockImplementation(() => new Promise((resolve) => {finishSave = resolve;}));
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const dialog = await openSettings();
        const select = await dialog.findByLabelText('Formación');
        fireEvent.click(dialog.getByRole('button', {name: 'Guardar equipo'}));

        expect(select).toBeDisabled();
        expect(dialog.getByRole('button', {name: 'Cancelar'})).toBeDisabled();
        expect(dialog.getByRole('button', {name: 'Guardando…'})).toBeDisabled();
        expect(dialog.queryByRole('button', {name: 'Close'})).not.toBeInTheDocument();
        fireEvent.keyDown(screen.getByRole('dialog'), {key: 'Escape'});
        expect(screen.getByRole('dialog')).toBeInTheDocument();

        await act(async () => finishSave(structuredClone(persisted)));
        expect(await dialog.findByText('Equipo guardado correctamente.')).toBeInTheDocument();
        expect(dialog.getByRole('button', {name: 'Cancelar'})).toBeEnabled();
    });

    it('mantiene formación, titulares, suplentes y comportamientos al paginar y guardar', async () => {
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const formation = await editor.findByLabelText('Formación');
        const original = structuredClone(persisted.lineUp);
        expect(editor.getByText('Jugador 10')).toBeInTheDocument();
        expect(getPlayersByIds).toHaveBeenCalledWith([10, 2, 3, 4, 5, 6], expect.anything());

        fireEvent.change(formation, {target: {value: '2'}});
        fireEvent.change(editor.getByLabelText('Buscar jugador para el lugar 1'), {target: {value: 'Jugador 11'}});
        fireEvent.click(await editor.findByRole('button', {name: 'Jugador 11'}));
        fireEvent.change(editor.getByLabelText('Comportamiento del lugar 1'), {target: {value: '11'}});
        fireEvent.click(editor.getByRole('button', {name: 'Suplentes'}));
        fireEvent.change(editor.getByLabelText('Buscar jugador para el lugar 4'), {target: {value: 'Jugador 12'}});
        fireEvent.click(await editor.findByRole('button', {name: 'Jugador 12'}));
        fireEvent.change(editor.getByLabelText('Comportamiento del lugar 4'), {target: {value: '11'}});

        let completePage;
        listPlayers.mockImplementationOnce(params => new Promise(resolve => {
            completePage = () => resolve(rosterPage(params));
        }));
        fireEvent.click(screen.getByRole('button', {name: 'Siguiente'}));
        expect(screen.getByText('Cargando jugadores…')).toBeInTheDocument();
        expect(editor.getByLabelText('Formación')).toBe(formation);
        expect(formation).toBeEnabled();
        await act(async () => completePage());

        expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
        expect(screen.queryByText('Cargando jugadores…')).not.toBeInTheDocument();
        expect(formation).toHaveValue('2');
        expect(editor.getByText('Jugador 12')).toBeInTheDocument();
        expect(editor.getByLabelText('Comportamiento del lugar 4')).toHaveValue('11');
        fireEvent.click(editor.getByRole('button', {name: 'Titulares'}));
        expect(editor.getByText('Jugador 11')).toBeInTheDocument();
        expect(editor.getByLabelText('Comportamiento del lugar 1')).toHaveValue('11');
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));
        expect(await editor.findByText('Equipo guardado correctamente.')).toBeInTheDocument();
        expect(updateDefaultTeam).toHaveBeenCalledWith({
            formationId: 2,
            starters: [{playerId: 11, behaviourId: 11}, ...original.starters.slice(1)],
            substitutes: [{playerId: 12, behaviourId: 11}, ...original.substitutes.slice(1)],
        });
        for (const fetchOnce of [getMyClub, listBehaviours, listMyLeagues, getDefaultTeam, getFormations]) {
            expect(fetchOnce).toHaveBeenCalledTimes(1);
        }
    });

    it('reintenta solamente la página del plantel que falló y mantiene el borrador disponible', async () => {
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const formation = await editor.findByLabelText('Formación');
        fireEvent.change(formation, {target: {value: '3'}});
        listPlayers.mockRejectedValueOnce(new Error('Sin conexión.'));

        fireEvent.click(screen.getByRole('button', {name: 'Siguiente'}));
        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar el plantel. Sin conexión.');
        expect(formation).toHaveValue('3');
        expect(formation).toBeEnabled();
        expect(editor.getByRole('button', {name: 'Guardar equipo'})).toBeEnabled();
        expect(screen.getByRole('button', {name: 'Configurar club'})).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', {name: 'Reintentar carga del plantel'}));
        expect(await screen.findByText('Jugador 12')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(editor.getByLabelText('Formación')).toBe(formation);
        expect(formation).toHaveValue('3');
        expect(listPlayers.mock.calls.map(([params]) => params.page)).toEqual([1, 2, 2]);
        expect(getDefaultTeam).toHaveBeenCalledTimes(1);
    });
});
