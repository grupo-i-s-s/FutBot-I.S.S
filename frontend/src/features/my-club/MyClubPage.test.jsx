import {act, cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import MyClubPage from './MyClubPage';
import {
    getDefaultTeam, getFormations, getMyClub, getPlayersByIds, listBehaviours, listDtBehaviours,
    listMyLeagues, listPlayers, updateDefaultTeam, updateDtSettings, updateMyClub,
} from './api';

vi.mock('./api', () => ({
    getDefaultTeam: vi.fn(), getFormations: vi.fn(),
    updateDefaultTeam: vi.fn(), updateMyClub: vi.fn(),
    getMyClub: vi.fn(), getPlayersByIds: vi.fn(),
    listBehaviours: vi.fn(), listMyLeagues: vi.fn(), listPlayers: vi.fn(),
    listDtBehaviours: vi.fn(), updateDtSettings: vi.fn(),
}));

const club = {id: 7, name: 'Club de prueba', avatar: 'shield', friendlyAvailable: true};
const behaviours = [{id: 10, name: 'Equilibrado'}, {id: 11, name: 'Ofensivo'}];
const players = Array.from({length: 12}, (_, index) => ({
    id: index + 1, name: `Jugador ${index + 1}`, behaviorId: 10,
    behaviourName: 'Equilibrado', power: 60, agility: 60,
    control: 60, speed: 60, strength: 60,
}));
let persisted;

function rosterPage({page, pageSize, search}) {
    const matching = search ? players.filter(player => player.name.includes(search)) : players;
    return {
        items: matching.slice((page - 1) * pageSize, page * pageSize),
        total: matching.length,
        totalPages: Math.max(1, Math.ceil(matching.length / pageSize)),
    };
}

async function openSettings() {
    fireEvent.click(await screen.findByRole('button', {name: 'Configurar club'}));
    return within(await screen.findByRole('dialog'));
}

async function teamEditor() {
    return within(await screen.findByRole('tabpanel', {name: 'Mi equipo'}));
}

async function saveToast(message) {
    const notifications = screen.getByRole('region', {name: /^Notificaciones de Mi club/});
    return within(notifications).findByText(message);
}

function searchCombobox(input, query) {
    act(() => input.focus());
    fireEvent.input(input, {target: {value: query}, inputType: 'insertText'});
}

async function chooseComboboxOption(input, query, name) {
    searchCombobox(input, query);
    fireEvent.click(await screen.findByRole('option', {name, exact: true}));
    expect(input).toHaveValue(name);
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
        listDtBehaviours.mockResolvedValue({items: []});
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

    it('guarda primero la formación y luego un comportamiento en Mi equipo y recupera ambos al volver', async () => {
        const {unmount} = render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const select = await editor.findByLabelText('Formación');
        expect(screen.getAllByRole('tab').map(tab => tab.textContent)).toEqual([
            'Mi equipo', 'Jugadores', 'Comportamientos', 'DT', 'Ligas inscriptas',
        ]);
        expect(screen.getByRole('tab', {name: 'Mi equipo', selected: true})).toBeInTheDocument();
        expect(editor.queryByRole('form', {name: 'Configuración del DT'})).not.toBeInTheDocument();
        expect(editor.getByRole('heading', {name: 'Titulares'})).toBeVisible();
        expect(editor.getByRole('heading', {name: 'Suplentes'})).toBeVisible();
        const player = editor.getByRole('combobox', {name: 'Jugador del lugar 1'});
        const behaviour = editor.getByRole('combobox', {name: 'Comportamiento del lugar 1'});
        expect(player).toHaveValue('Jugador 10');
        expect(behaviour).toHaveValue('Equilibrado');
        expect(editor.getByRole('combobox', {name: 'Jugador del lugar 4'})).toHaveValue('Jugador 4');
        expect(editor.getByRole('combobox', {name: 'Comportamiento del lugar 4'})).toHaveValue('Equilibrado');
        expect(select).toHaveValue('1');
        expect(editor.getAllByRole('option', {name: /^(2-1|1-2|1-1-1)$/})).toHaveLength(3);
        expect(document.querySelector('form form')).toBeNull();
        expect(document.querySelector('canvas')).toBeNull();
        expect(document.querySelector('svg[aria-label^="Distribución"]')).toBeNull();
        const original = structuredClone(persisted.lineUp);

        for (const [input, query, option, selected] of [
            [player, 'Jugador 11', 'Jugador 11', 'Jugador 10'],
            [behaviour, 'Ofen', 'Ofensivo', 'Equilibrado'],
        ]) {
            searchCombobox(input, query);
            expect(await screen.findByRole('option', {name: option, exact: true})).toBeVisible();
            fireEvent.keyDown(input, {key: 'Escape'});
            await waitFor(() => expect(input).toHaveValue(selected));
        }

        fireEvent.change(select, {target: {value: '2'}});
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));
        expect(await saveToast('Equipo guardado correctamente.')).toBeVisible();
        const savedFormation = {...original, formationId: 2};
        expect(updateDefaultTeam).toHaveBeenNthCalledWith(1, savedFormation);

        fireEvent.click(screen.getByRole('button', {name: 'Cerrar notificación'}));
        await waitFor(() => expect(screen.queryByText('Equipo guardado correctamente.')).not.toBeInTheDocument());
        await chooseComboboxOption(behaviour, 'Ofen', 'Ofensivo');
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));
        expect(await saveToast('Equipo guardado correctamente.')).toBeVisible();
        expect(updateDefaultTeam).toHaveBeenNthCalledWith(2, {
            ...savedFormation,
            starters: [{...original.starters[0], behaviourId: 11}, ...original.starters.slice(1)],
        });
        expect(updateDefaultTeam).toHaveBeenCalledTimes(2);
        expect(updateMyClub).not.toHaveBeenCalled();

        unmount();
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const reopened = await teamEditor();
        expect(await reopened.findByLabelText('Formación')).toHaveValue('2');
        expect(screen.queryByText('Equipo guardado correctamente.')).not.toBeInTheDocument();
        expect(reopened.getByRole('combobox', {name: 'Jugador del lugar 1'})).toHaveValue('Jugador 10');
        expect(reopened.getByRole('combobox', {name: 'Comportamiento del lugar 1'})).toHaveValue('Ofensivo');
    });

    it('conserva la selección si falla el guardado y muestra el error', async () => {
        updateDefaultTeam.mockRejectedValue(new Error('No se pudo guardar la formación.'));
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const select = await editor.findByLabelText('Formación');
        fireEvent.change(select, {target: {value: '3'}});
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));

        expect(await editor.findByRole('alert')).toHaveTextContent('No se pudo guardar la formación.');
        expect(screen.queryByText('Equipo guardado correctamente.')).not.toBeInTheDocument();
        expect(select).toHaveValue('3');
        expect(persisted.lineUp.formationId).toBe(1);
        expect(editor.getByRole('button', {name: 'Guardar equipo'})).toBeEnabled();
    });

    it('bloquea el guardado duplicado y muestra el toast si el guardado termina en otra pestaña', async () => {
        const save = Promise.withResolvers();
        updateDefaultTeam.mockReturnValueOnce(save.promise);
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const select = await editor.findByLabelText('Formación');
        const form = editor.getByRole('form', {name: 'Equipo para próximos partidos'});
        fireEvent.change(select, {target: {value: '2'}});
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));

        expect(select).toBeDisabled();
        expect(editor.getByRole('button', {name: /^Guardando/})).toBeDisabled();
        fireEvent.submit(form);
        expect(updateDefaultTeam).toHaveBeenCalledTimes(1);

        fireEvent.click(screen.getByRole('tab', {name: 'Jugadores'}));
        await screen.findByRole('tabpanel', {name: 'Jugadores'});
        expect(select).not.toBeVisible();
        expect(screen.queryByText('Equipo guardado correctamente.')).not.toBeInTheDocument();

        await act(async () => save.resolve({clubId: 7, lineUp: {...persisted.lineUp, formationId: 2}}));
        expect(await saveToast('Equipo guardado correctamente.')).toBeVisible();
        fireEvent.click(screen.getByRole('tab', {name: 'Mi equipo'}));
        expect((await teamEditor()).getByLabelText('Formación')).toHaveValue('2');
        expect(editor.getByRole('button', {name: 'Guardar equipo'})).toBeEnabled();
    });

    it('edita solo el perfil desde Configurar club y conserva el borrador de Mi equipo', async () => {
        const name = 'Club actualizado';
        const profile = {name, avatar: 'avatar-02.png', friendlyAvailable: false};
        const message = 'Los cambios del club se guardaron correctamente.';
        updateMyClub.mockResolvedValue({...club, ...profile});
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const formation = await editor.findByLabelText('Formación');
        fireEvent.change(formation, {target: {value: '3'}});

        const dialog = await openSettings();
        expect(dialog.queryByLabelText('Formación')).not.toBeInTheDocument();
        expect(dialog.queryByRole('button', {name: 'Guardar equipo'})).not.toBeInTheDocument();
        fireEvent.change(dialog.getByRole('textbox', {name: 'Nombre del club'}), {target: {value: name}});
        fireEvent.click(dialog.getByRole('button', {name: 'Escudo 02'}));
        fireEvent.click(dialog.getByRole('switch', {name: 'Disponible para amistosos'}));
        fireEvent.click(dialog.getByRole('button', {name: 'Guardar cambios'}));

        expect(updateMyClub).toHaveBeenCalledExactlyOnceWith(profile);
        expect(await screen.findByRole('heading', {name})).toBeVisible();
        expect(await saveToast(message)).toBeVisible();
        fireEvent.click(await screen.findByRole('button', {name: 'Cerrar notificación'}));
        await waitFor(() => expect(screen.queryByText(message)).not.toBeInTheDocument());
        expect((await teamEditor()).getByLabelText('Formación')).toHaveValue('3');
        expect(getDefaultTeam).toHaveBeenCalledTimes(1);
        expect(updateDefaultTeam).not.toHaveBeenCalled();
    });

    it('confirma la creación y el guardado del DT con toasts de Mi club', async () => {
        const notice = 'Comportamiento del DT creado. Ya podés seleccionarlo y guardar el DT.';
        const entry = {pathname: '/mi-club', state: {tab: 'dt', notice}};
        const updatedDt = {isActive: true, activeBehaviourId: 42};
        listDtBehaviours.mockResolvedValue({items: [{id: 42, name: 'Cuidar el resultado'}]});
        updateDtSettings.mockResolvedValue(updatedDt);
        render(<MemoryRouter initialEntries={[entry]}><MyClubPage/></MemoryRouter>);

        const editor = within(await screen.findByRole('tabpanel', {name: 'DT'}));
        expect(await saveToast(notice)).toBeVisible();
        const select = await editor.findByLabelText('Comportamiento del DT');
        fireEvent.change(select, {target: {value: '42'}});
        fireEvent.click(editor.getByRole('switch', {name: 'Activar DT para próximos partidos'}));
        fireEvent.click(editor.getByRole('button', {name: 'Guardar DT'}));

        expect(updateDtSettings).toHaveBeenCalledWith(updatedDt);
        expect(await saveToast('Configuración del DT guardada.')).toBeVisible();

        fireEvent.click(screen.getByRole('tab', {name: 'Mi equipo'}));
        fireEvent.click(screen.getByRole('tab', {name: 'DT'}));
        expect(editor.getByLabelText('Comportamiento del DT')).toHaveValue('42');
        expect(editor.getByRole('switch', {name: 'Activar DT para próximos partidos'})).toBeChecked();
    });

    it('mantiene el borrador al cambiar de pestaña y paginar el plantel', async () => {
        listMyLeagues.mockResolvedValueOnce({items: [
            {id: 42, name: 'Liga del club', type: 'PUBLIC', teams: 3, maxTeams: 8, status: 'open'},
        ]});
        render(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const formation = await editor.findByLabelText('Formación');
        const original = structuredClone(persisted.lineUp);
        const starter = editor.getByRole('combobox', {name: 'Jugador del lugar 1'});
        const starterBehaviour = editor.getByRole('combobox', {name: 'Comportamiento del lugar 1'});
        const substitute = editor.getByRole('combobox', {name: 'Jugador del lugar 4'});
        const substituteBehaviour = editor.getByRole('combobox', {name: 'Comportamiento del lugar 4'});
        expect(starter).toHaveValue('Jugador 10');
        expect(getPlayersByIds).toHaveBeenCalledWith([10, 2, 3, 4, 5, 6], expect.anything());

        fireEvent.change(formation, {target: {value: '2'}});
        await chooseComboboxOption(starter, 'Jugador 11', 'Jugador 11');
        await chooseComboboxOption(starterBehaviour, 'Ofen', 'Ofensivo');
        await chooseComboboxOption(substitute, 'Jugador 12', 'Jugador 12');
        await chooseComboboxOption(substituteBehaviour, 'Ofen', 'Ofensivo');

        fireEvent.click(screen.getByRole('tab', {name: 'Jugadores'}));
        const roster = within(await screen.findByRole('tabpanel', {name: 'Jugadores'}));
        await waitFor(() => expect(formation).not.toBeVisible());
        expect(roster.getByText('12 jugadores en el plantel')).toBeInTheDocument();
        expect(roster.queryByRole('combobox')).not.toBeInTheDocument();

        let completePage;
        listPlayers.mockImplementationOnce(params => new Promise(resolve => {
            completePage = () => resolve(rosterPage(params));
        }));
        fireEvent.click(roster.getByRole('button', {name: 'Siguiente'}));
        expect(roster.getByText('Cargando jugadores…')).toBeInTheDocument();
        await act(async () => completePage());

        expect(roster.getByText('Página 2 de 2')).toBeInTheDocument();
        expect(roster.getByText('Jugador 12')).toBeInTheDocument();
        expect(roster.queryByText('Cargando jugadores…')).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('tab', {name: 'Comportamientos'}));
        const catalog = within(await screen.findByRole('tabpanel', {name: 'Comportamientos'}));
        for (const {id, name} of behaviours) {
            expect(catalog.getByText(name)).toBeInTheDocument();
            expect(catalog.getByRole('link', {name: `Ver detalle de ${name}`})).toHaveAttribute('href', `/comportamientos/${id}`);
        }
        expect(catalog.getByRole('link', {name: 'Gestionar comportamientos'})).toHaveAttribute('href', '/comportamientos');

        expect(screen.queryByText('Liga del club')).not.toBeInTheDocument();
        fireEvent.click(screen.getByRole('tab', {name: 'Ligas inscriptas'}));
        const leagues = within(await screen.findByRole('tabpanel', {name: 'Ligas inscriptas'}));
        expect(leagues.getByText('Liga del club')).toBeVisible();
        expect(leagues.getByRole('link', {name: 'Ver lobby de Liga del club'})).toHaveAttribute('href', '/ligas/42/sala-de-espera');

        fireEvent.click(screen.getByRole('tab', {name: 'Mi equipo'}));
        expect((await teamEditor()).getByLabelText('Formación')).toBe(formation);
        expect(formation).toBeEnabled();
        expect(formation).toHaveValue('2');
        expect(substitute).toHaveValue('Jugador 12');
        expect(substituteBehaviour).toHaveValue('Ofensivo');
        expect(starter).toHaveValue('Jugador 11');
        expect(starterBehaviour).toHaveValue('Ofensivo');
        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));
        expect(await saveToast('Equipo guardado correctamente.')).toBeVisible();
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

        fireEvent.click(screen.getByRole('tab', {name: 'Jugadores'}));
        fireEvent.click(screen.getByRole('button', {name: 'Siguiente'}));
        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar el plantel. Sin conexión.');
        expect(screen.getByRole('button', {name: 'Configurar club'})).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', {name: 'Reintentar carga del plantel'}));
        expect(await screen.findByText('Jugador 12')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        fireEvent.click(screen.getByRole('tab', {name: 'Mi equipo'}));
        await teamEditor();
        expect(editor.getByLabelText('Formación')).toBe(formation);
        expect(formation).toHaveValue('3');
        expect(editor.getByRole('button', {name: 'Guardar equipo'})).toBeEnabled();
        expect(listPlayers.mock.calls.map(([params]) => params.page)).toEqual([1, 2, 2]);
        expect(getDefaultTeam).toHaveBeenCalledTimes(1);
    });
});
