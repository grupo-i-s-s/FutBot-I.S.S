import {useRef, useState} from 'react';
import {Link, useNavigate} from 'react-router';
import {Button} from '@/components/ui/button';
import {createBehaviour, createDtBehaviour, validateBehaviour} from './api';
import BehaviourCodeEditor from '../behaviours/components/BehaviourCodeEditor';
import {useUnsavedChanges} from '../behaviours/hooks/useUnsavedChanges';

const PLAYER_TEMPLATE = 'def decide(observation):\n    return ir_a_pelota()\n';

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

export default function CreateBehaviourPage({kind = 'PLAYER'}) {
    return <BehaviourCreationForm key={kind} kind={kind}/>;
}

function BehaviourCreationForm({kind}) {
    const isDt = kind === 'DT';
    const template = isDt ? DT_TEMPLATE : PLAYER_TEMPLATE;
    const [name, setName] = useState('');
    const [code, setCode] = useState(template);
    const [error, setError] = useState('');
    const [diagnostics, setDiagnostics] = useState([]);
    const [isValid, setIsValid] = useState(false);
    const [action, setAction] = useState('');
    const pending = useRef(false);
    const navigate = useNavigate();
    const allowNavigation = useUnsavedChanges(name !== '' || code !== template);

    function clearFeedback() {
        setError('');
        setDiagnostics([]);
        setIsValid(false);
    }

    async function handleValidate() {
        if (pending.current || !code.trim()) return;
        pending.current = true;
        clearFeedback();
        setAction('validate');

        try {
            const result = await validateBehaviour(isDt ? 'COACH' : 'PLAYER', code);
            setIsValid(result.valid);
            setDiagnostics(result.diagnostics ?? []);
            if (!result.valid) setError('Revisá el código antes de guardarlo.');
        } catch (err) {
            setError(err.message || 'No se pudo validar el comportamiento.');
            setDiagnostics(err.diagnostics ?? []);
        } finally {
            pending.current = false;
            setAction('');
        }
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (pending.current) return;
        clearFeedback();

        if (!name.trim() || !code.trim()) {
            setError('Deben completarse todos los campos.');
            return;
        }

        pending.current = true;
        setAction('save');

        try {
            if (isDt) {
                await createDtBehaviour(name.trim(), code);
                allowNavigation();
                navigate('/mi-club', {
                    replace: true,
                    state: {notice: 'Comportamiento del DT creado. Ya podés seleccionarlo y guardar el DT.'},
                });
            } else {
                await createBehaviour(name, code);
                allowNavigation();
                navigate('/behaviours', {
                    replace: true,
                    state: {notice: 'Comportamiento creado exitosamente.'},
                });
            }
        } catch (err) {
            const fields = Object.values(err.fields ?? {});
            setError(fields.join(' ') || err.message || 'No se pudo crear el comportamiento.');
            setDiagnostics(err.diagnostics ?? []);
        } finally {
            pending.current = false;
            setAction('');
        }
    }

    return (
        <div className="max-w-4xl mx-auto p-6 flex flex-col">
            {isDt && <Link to="/mi-club" className="mb-4 text-sm underline">Volver a Mi club</Link>}
            <h2 className="text-2xl font-bold mb-6 text-gray-800">
                {isDt ? 'Crear comportamiento del DT' : 'Crear Comportamiento'}
            </h2>
            <form onSubmit={handleSubmit} className="w-full space-y-4">
                <div>
                    <label htmlFor="behaviour-name" className="sr-only">Nombre del comportamiento</label>
                    <input
                        id="behaviour-name"
                        type="text"
                        placeholder="Ingrese el nombre"
                        maxLength={isDt ? 30 : 50}
                        value={name}
                        disabled={Boolean(action)}
                        className="w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <BehaviourCodeEditor
                    value={code}
                    onChange={(value) => {
                        setCode(value);
                        clearFeedback();
                    }}
                    diagnostics={diagnostics}
                    documentId="new"
                    kind={isDt ? 'COACH' : 'PLAYER'}
                    readOnly={Boolean(action)}
                    functions={isDt ? dtApiFunctions : undefined}
                    helpDescription={isDt
                        ? 'Escribí una función decide(obs) que devuelva DtAction con los cambios tácticos y las sustituciones del equipo.'
                        : undefined}
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
