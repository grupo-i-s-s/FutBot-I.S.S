import {act, cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {createMemoryRouter, Link, MemoryRouter, Route, RouterProvider, Routes, useLocation} from 'react-router';
import {toast} from 'sonner';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {Toaster} from '@/components/ui/sonner';

import MyClubPage from './MyClubPage';
import {deleteBehaviour, getBehaviour, getBehaviourUsage, updateBehaviour} from '../behaviours/api.js';
import {createBehaviour} from '../create-behaviour/api.js';
import {createPlayer} from '../create-players/api.js';
import {listMyFriendlyMatches} from '../friendly-matches/api.js';
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

vi.mock('../friendly-matches/api.js', () => ({listMyFriendlyMatches: vi.fn()}));
vi.mock('../create-players/api.js', () => ({createPlayer: vi.fn()}));
vi.mock('../create-behaviour/api.js', () => ({createBehaviour: vi.fn()}));
vi.mock('../behaviours/api.js', () => ({
    createBehaviourTestMatch: vi.fn(),
    deleteBehaviour: vi.fn(), getBehaviour: vi.fn(), getBehaviourUsage: vi.fn(), updateBehaviour: vi.fn(),
}));
vi.mock('@monaco-editor/react', () => ({default: () => null}));

const club = {id: 7, name: 'Club de prueba', avatar: 'shield', friendlyAvailable: true};
const behaviours = [{id: 10, name: 'Equilibrado'}, {id: 11, name: 'Ofensivo'}];
const players = Array.from({length: 12}, (_, index) => ({
    id: index + 1, name: `Jugador ${index + 1}`, behaviorId: 10,
    behaviourName: 'Equilibrado', power: 60, agility: 60,
    control: 60, speed: 60, strength: 60,
}));
let persisted;

function rosterPage({page, pageSize, search}, roster = players) {
    const matching = search ? roster.filter(player => player.name.includes(search)) : roster;
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
    const notifications = screen.getByRole('region', {name: /^Notificaciones/});
    return within(notifications).findByText(message);
}

function renderWithToaster(ui) {
    return render(<>
        {ui}
        <Toaster closeButton containerAriaLabel="Notificaciones" toastOptions={{closeButtonAriaLabel: 'Cerrar notificación'}} />
    </>);
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

function MatchReturnLink() {
    const {state} = useLocation();
    return <Link to={state.returnTo}>Volver a amistosos</Link>;
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

    afterEach(() => {
        cleanup();
        toast.dismiss();
    });

    it('guarda primero la formación y luego un comportamiento en Mi equipo y recupera ambos al volver', async () => {
        const {unmount} = renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const select = await editor.findByLabelText('Formación');
        expect(screen.getAllByRole('tab').map(tab => tab.textContent)).toEqual([
            'Mi equipo', 'Jugadores', 'Comportamientos', 'DT', 'Ligas inscriptas', 'Mis amistosos',
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
        renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const reopened = await teamEditor();
        expect(await reopened.findByLabelText('Formación')).toHaveValue('2');
        expect(screen.queryByText('Equipo guardado correctamente.')).not.toBeInTheDocument();
        expect(reopened.getByRole('combobox', {name: 'Jugador del lugar 1'})).toHaveValue('Jugador 10');
        expect(reopened.getByRole('combobox', {name: 'Comportamiento del lugar 1'})).toHaveValue('Ofensivo');
    });

    it('carga Mis amistosos al seleccionar la pestaña y vuelve a ella desde un partido', async () => {
        listMyFriendlyMatches.mockResolvedValue([{
            matchId: 22,
            creatorClubName: 'Club rival',
            visitorClubName: club.name,
            startDateTime: '2026-11-09T21:30:00Z',
            status: 'SCHEDULED',
            isCreator: false,
        }]);
        renderWithToaster(
            <MemoryRouter initialEntries={['/mi-club']}>
                <Routes>
                    <Route path="/mi-club" element={<MyClubPage />} />
                    <Route path="/partidos/:matchId" element={<MatchReturnLink />} />
                </Routes>
            </MemoryRouter>,
        );
        const tab = await screen.findByRole('tab', {name: 'Mis amistosos'});
        expect(listMyFriendlyMatches).not.toHaveBeenCalled();
        fireEvent.click(tab);

        const matches = within(await screen.findByRole('tabpanel', {name: 'Mis amistosos'}));
        const match = await matches.findByRole('link', {name: 'Ver partido 22'});
        expect(match).toHaveAttribute('href', '/partidos/22');
        expect(matches.getByText('Club rival vs. Club de prueba')).toBeVisible();
        expect(matches.getByText('Programado')).toBeVisible();
        expect(matches.getByText('Tu club es visitante')).toBeVisible();
        expect(listMyFriendlyMatches).toHaveBeenCalledTimes(1);

        fireEvent.click(match);
        const back = screen.getByRole('link', {name: 'Volver a amistosos'});
        expect(back).toHaveAttribute('href', '/mi-club?tab=amistosos');
        fireEvent.click(back);
        expect(await screen.findByRole('tab', {name: 'Mis amistosos', selected: true})).toBeVisible();
        expect(await screen.findByRole('link', {name: 'Ver partido 22'})).toBeVisible();
    });

    it('intercambia un titular y un suplente con sus comportamientos y guarda los seis lugares en orden', async () => {
        const original = persisted.lineUp;
        original.substitutes[0].behaviourId = 11;
        const {unmount} = renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const editor = await teamEditor();
        const starter = await editor.findByRole('combobox', {name: 'Jugador del lugar 1'});

        function expectSwappedLineup(view) {
            expect(view.getAllByRole('combobox', {name: /^Jugador del lugar /}).map(input => input.value)).toEqual([
                'Jugador 4', 'Jugador 2', 'Jugador 3', 'Jugador 10', 'Jugador 5', 'Jugador 6',
            ]);
            expect(view.getByRole('combobox', {name: 'Comportamiento del lugar 1'})).toHaveValue('Ofensivo');
            expect(view.getByRole('combobox', {name: 'Comportamiento del lugar 4'})).toHaveValue('Equilibrado');
        }

        await chooseComboboxOption(starter, 'Jugador 4', 'Jugador 4');
        expect(listPlayers).toHaveBeenCalledWith(expect.objectContaining({search: 'Jugador 4', page: 1, pageSize: 10}));
        expectSwappedLineup(editor);

        fireEvent.click(editor.getByRole('button', {name: 'Guardar equipo'}));
        expect(await saveToast('Equipo guardado correctamente.')).toBeVisible();
        expect(updateDefaultTeam).toHaveBeenCalledExactlyOnceWith({
            formationId: original.formationId,
            starters: [original.substitutes[0], ...original.starters.slice(1)],
            substitutes: [original.starters[0], ...original.substitutes.slice(1)],
        });

        unmount();
        renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
        const reopened = await teamEditor();
        await reopened.findByLabelText('Formación');
        expectSwappedLineup(reopened);
    });

    it('conserva la selección si falla el guardado y muestra el error', async () => {
        updateDefaultTeam.mockRejectedValue(new Error('No se pudo guardar la formación.'));
        renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
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
        renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
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
        renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
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
        renderWithToaster(<MemoryRouter initialEntries={[entry]}><MyClubPage/></MemoryRouter>);

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
        renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
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
        await chooseComboboxOption(starterBehaviour, 'Ofen', 'Ofensivo');
        await chooseComboboxOption(starter, 'Jugador 11', 'Jugador 11');
        expect(starterBehaviour).toHaveValue('Equilibrado');
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
        for (const {name} of behaviours) {
            expect(catalog.getByText(name)).toBeInTheDocument();
            expect(catalog.getByRole('button', {name: `Ver detalle de ${name}`})).toBeEnabled();
        }
        expect(catalog.getByRole('button', {name: 'Crear nuevo comportamiento'})).toBeEnabled();
        expect(catalog.getByRole('button', {name: 'Probar comportamiento'})).toBeEnabled();
        expect(catalog.queryByRole('link', {name: 'Gestionar comportamientos'})).not.toBeInTheDocument();

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

    it('agrega el comportamiento creado al catálogo y lo deja disponible para el equipo', async () => {
        const created = {id: 12, name: 'Presión lateral', description: '', kind: 'PLAYER', version: 1, validationStatus: 'VALID'};
        createBehaviour.mockResolvedValueOnce(created);
        const router = createMemoryRouter([{path: '/mi-club', element: <MyClubPage/>}], {
            initialEntries: ['/mi-club?tab=behaviours'],
        });
        renderWithToaster(<RouterProvider router={router}/>);

        const catalog = within(await screen.findByRole('tabpanel', {name: 'Comportamientos'}));
        fireEvent.click(catalog.getByRole('button', {name: 'Crear nuevo comportamiento'}));
        const form = within(await screen.findByRole('dialog', {name: 'Crear comportamiento'}));
        fireEvent.change(form.getByLabelText('Nombre del comportamiento'), {target: {value: created.name}});
        fireEvent.click(form.getByRole('button', {name: 'Guardar comportamiento'}));

        expect(await catalog.findByRole('button', {name: `Ver detalle de ${created.name}`})).toBeVisible();
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(await saveToast('Comportamiento creado')).toBeVisible();
        expect(router.state.location.search).toBe('?tab=behaviours');
        expect(createBehaviour).toHaveBeenCalledExactlyOnceWith(created.name, expect.stringContaining('def decide'));

        fireEvent.click(screen.getByRole('tab', {name: 'Mi equipo'}));
        const editor = await teamEditor();
        await chooseComboboxOption(editor.getByRole('combobox', {name: 'Comportamiento del lugar 1'}), 'Presión', created.name);
        expect(listBehaviours).toHaveBeenCalledTimes(1);
    });

    it('consulta el código al abrir el detalle y permite reintentar sin salir de la pestaña', async () => {
        const behaviour = behaviours[0];
        const code = 'def decide(observation):\n    return ir_a_pelota()\n';
        getBehaviour
            .mockRejectedValueOnce(new Error('No se pudo cargar el código.'))
            .mockResolvedValueOnce({...behaviour, code});
        const router = createMemoryRouter([{path: '/mi-club', element: <MyClubPage/>}], {
            initialEntries: ['/mi-club?tab=behaviours'],
        });
        render(<RouterProvider router={router}/>);

        const trigger = await screen.findByRole('button', {name: `Ver detalle de ${behaviour.name}`});
        expect(getBehaviour).not.toHaveBeenCalled();
        fireEvent.click(trigger);
        const detail = within(await screen.findByRole('dialog', {name: 'Detalle de comportamiento'}));
        expect(await detail.findByRole('alert')).toHaveTextContent('No se pudo cargar el código.');
        fireEvent.click(detail.getByRole('button', {name: 'Reintentar'}));

        const source = await detail.findByRole('region', {name: 'Código del comportamiento'});
        expect(source.textContent).toBe(code);
        expect(detail.queryByRole('textbox')).not.toBeInTheDocument();
        expect(getBehaviour.mock.calls.map(([id]) => id)).toEqual([behaviour.id, behaviour.id]);
        fireEvent.click(detail.getByRole('button', {name: 'Cerrar'}));
        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
        expect(router.state.location).toMatchObject({pathname: '/mi-club', search: '?tab=behaviours'});
    });

    it('sincroniza la edición y eliminación del catálogo con el borrador de Mi equipo', async () => {
        const detail = {id: 12, name: 'Ataque lateral', kind: 'PLAYER', code: 'return', version: 1, validationStatus: 'VALID'};
        const description = 'Avance por la banda';
        listBehaviours.mockResolvedValueOnce({items: [...behaviours, {...detail, description}]});
        getBehaviour.mockResolvedValueOnce(detail);
        getBehaviourUsage.mockResolvedValueOnce({inUse: false, references: {}});
        updateBehaviour.mockResolvedValueOnce({...detail, name: 'Presión alta', version: 2});
        deleteBehaviour.mockResolvedValueOnce(null);
        const router = createMemoryRouter([{path: '/mi-club', element: <MyClubPage/>}], {
            initialEntries: ['/mi-club'],
        });
        renderWithToaster(<RouterProvider router={router}/>);

        const editor = await teamEditor();
        const formation = await editor.findByLabelText('Formación');
        const selection = editor.getByRole('combobox', {name: 'Comportamiento del lugar 1'});
        fireEvent.change(formation, {target: {value: '2'}});
        await chooseComboboxOption(selection, 'Ataque lateral', detail.name);

        fireEvent.click(screen.getByRole('tab', {name: 'Comportamientos'}));
        const catalog = within(await screen.findByRole('tabpanel', {name: 'Comportamientos'}));
        fireEvent.click(catalog.getByRole('button', {name: `Editar ${detail.name}`}));
        const edit = within(await screen.findByRole('dialog', {name: 'Editar comportamiento'}));
        fireEvent.change(await edit.findByLabelText('Nombre del comportamiento'), {target: {value: 'Presión alta'}});
        fireEvent.click(edit.getByRole('button', {name: 'Guardar cambios'}));

        expect(await catalog.findByText('Presión alta')).toBeVisible();
        expect(catalog.getByText(description)).toBeVisible();
        expect(await saveToast('Comportamiento actualizado')).toBeVisible();
        expect(updateBehaviour).toHaveBeenCalledWith(12, {name: 'Presión alta', code: detail.code, expectedVersion: 1});

        fireEvent.click(screen.getByRole('tab', {name: 'Mi equipo'}));
        expect((await teamEditor()).getByLabelText('Formación')).toHaveValue('2');
        expect(selection).toHaveValue('Presión alta');
        fireEvent.click(screen.getByRole('tab', {name: 'Comportamientos'}));
        fireEvent.click(await screen.findByRole('button', {name: 'Eliminar Presión alta'}));
        const deletion = within(await screen.findByRole('dialog'));
        fireEvent.click(deletion.getByRole('button', {name: 'Eliminar'}));

        expect(await saveToast('Comportamiento eliminado')).toBeVisible();
        expect(screen.queryByRole('button', {name: 'Editar Presión alta'})).not.toBeInTheDocument();
        expect(deleteBehaviour).toHaveBeenCalledWith(12);
        fireEvent.click(screen.getByRole('tab', {name: 'Mi equipo'}));
        expect((await teamEditor()).getByLabelText('Formación')).toHaveValue('2');
        expect(selection).toHaveValue('');
        expect(listBehaviours).toHaveBeenCalledTimes(1);
        expect(getDefaultTeam).toHaveBeenCalledTimes(1);
    });

    it('crea un jugador desde el modal y lo muestra en la última página de Jugadores', async () => {
        const newPlayer = {...players[0], id: 13, name: 'Fichaje nuevo'};
        let roster = players;
        listPlayers.mockImplementation(async params => rosterPage(params, roster));
        createPlayer.mockImplementation(async () => {
            roster = [...players, newPlayer];
            return newPlayer;
        });

        renderWithToaster(<MemoryRouter initialEntries={['/mi-club?tab=players']}><MyClubPage/></MemoryRouter>);
        const panel = within(await screen.findByRole('tabpanel', {name: 'Jugadores'}));
        expect(await panel.findByText('Jugador 1')).toBeVisible();
        expect(panel.getByText('Página 1 de 2')).toBeVisible();

        fireEvent.click(panel.getByRole('button', {name: 'Crear jugador'}));
        const dialog = within(await screen.findByRole('dialog', {name: 'Crear jugador'}));
        fireEvent.change(dialog.getByLabelText('Nombre del jugador'), {target: {value: newPlayer.name}});
        fireEvent.click(dialog.getByRole('button', {name: 'Crear jugador'}));

        expect(await panel.findByText(newPlayer.name)).toBeVisible();
        expect(panel.getByText('Página 2 de 2')).toBeVisible();
        expect(panel.getByText('13 jugadores en el plantel')).toBeVisible();
        expect(screen.getByRole('tab', {name: 'Jugadores', selected: true})).toBeVisible();
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(await saveToast('Jugador creado')).toBeVisible();
        expect(createPlayer).toHaveBeenCalledExactlyOnceWith(newPlayer.name, 60, 60, 60, 60, 60);
        expect(listPlayers.mock.calls.map(([params]) => params.page)).toEqual([1, 2]);
        expect(getMyClub).toHaveBeenCalledTimes(1);
    });

    it('reintenta solamente la página del plantel que falló y mantiene el borrador disponible', async () => {
        renderWithToaster(<MemoryRouter><MyClubPage/></MemoryRouter>);
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
