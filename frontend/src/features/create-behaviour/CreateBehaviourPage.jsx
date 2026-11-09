import {Link, useNavigate} from 'react-router';
import {Button} from '@/components/ui/button';
import {routes} from '@/routes.js';
import BehaviourCodeEditor from '../behaviours/components/BehaviourCodeEditor';
import {useUnsavedChanges} from '../behaviours/hooks/useUnsavedChanges';
import {createDtBehaviour} from './api.js';
import {useBehaviourCreation} from './useBehaviourCreation.js';

const DT_TEMPLATE = [
    'from primitives.dt_behaviour import DtAction',
    'from primitives.behaviours import BehaviourMode',
    '',
    'def decide(obs):',
    '    cambios = [',
    '        cambiar_comportamiento(jugador, BehaviourMode.DEFENSIVE)',
    '        for jugador in obs.players_id',
    '    ]',
    '    if obs.can_substitute:',
    '        cambio = sustituir(obs.players_id[0], obs.substitutes_id[0])',
    '        return DtAction(cambios, [cambio])',
    '    return DtAction(cambios)',
].join('\n');

const dtApiFunctions = [
    {name: 'obs.time_played', description: 'Tiempo de juego transcurrido en segundos.'},
    {name: 'obs.my_goals / obs.rival_goals', description: 'Goles de tu equipo y del rival.'},
    {name: 'obs.players_id / obs.substitutes_id', description: 'Identificadores de los jugadores en cancha y del banco.'},
    {name: 'obs.can_substitute', description: 'Indica que el DT puede pedir una sustitución en la pausa actual.'},
    {name: 'obs.pause_index', description: 'Vale 1, 2 o 3 durante una pausa. El 2 corresponde al entretiempo.'},
    {name: 'cambiar_comportamiento(jugador, modo)', description: 'Acepta BehaviourMode.BALANCED, BehaviourMode.OFFENSIVE y BehaviourMode.DEFENSIVE.'},
    {name: 'sustituir(titular, suplente)', description: 'Pide un cambio durante una pausa con cuota disponible.'},
    {name: 'DtAction(cambios, sustituciones)', description: 'Devuelve las órdenes que evaluará el motor. La lista de sustituciones es opcional.'},
];

export default function CreateBehaviourPage() {
    const navigate = useNavigate();
    const {
        name, setName, code, changeCode, error, diagnostics, isValid, action, dirty, handleValidate, handleSubmit,
    } = useBehaviourCreation({
        kind: 'COACH', template: DT_TEMPLATE, create: createDtBehaviour, onCreated: handleCreated,
    });
    const allowNavigation = useUnsavedChanges(dirty);

    function handleCreated() {
        allowNavigation();
        navigate(routes.myClub, {
            replace: true,
            state: {tab: 'dt', notice: 'Comportamiento del DT creado. Ya podés seleccionarlo y guardar el DT.'},
        });
    }

    return (
        <div className="max-w-4xl mx-auto p-6 flex flex-col">
            <Link to={routes.myClub} state={{tab: 'dt'}} className="mb-4 text-sm underline">Volver a Mi club</Link>
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Crear comportamiento del DT</h2>
            <form onSubmit={handleSubmit} className="w-full space-y-4">
                <div>
                    <label htmlFor="behaviour-name" className="sr-only">Nombre del comportamiento</label>
                    <input
                        id="behaviour-name"
                        type="text"
                        placeholder="Ingrese el nombre"
                        maxLength={30}
                        value={name}
                        disabled={Boolean(action)}
                        className="w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <BehaviourCodeEditor
                    value={code}
                    onChange={changeCode}
                    diagnostics={diagnostics}
                    documentId="new"
                    kind="COACH"
                    readOnly={Boolean(action)}
                    functions={dtApiFunctions}
                    helpDescription="Escribí una función decide(obs) que devuelva DtAction con los cambios tácticos y las sustituciones del equipo."
                />
                <div className="flex flex-wrap justify-end gap-2">
                    <Button type="button" variant="outline" onClick={handleValidate} disabled={Boolean(action) || !code.trim()}>
                        {action === 'validate' ? 'Validando…' : 'Validar código'}
                    </Button>
                    <Button type="submit" disabled={Boolean(action)}>
                        {action === 'save' ? 'Guardando…' : 'Guardar Comportamiento'}
                    </Button>
                </div>
                {error && <p role="alert" className="text-destructive">{error}</p>}
                {isValid && <p role="status">El código es válido.</p>}
            </form>
        </div>
    );
}
