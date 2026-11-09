import Editor from "@monaco-editor/react";
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { createBehaviour, createDtBehaviour, validateBehaviour } from './api';
import { Button } from '@/components/ui/button';

const PLAYER_TEMPLATE = `def decide(observation):
    #return ir_a_pelota()`;

const DT_TEMPLATE = `from primitives.dt_behaviour import DtAction
from primitives.behaviours import BehaviourMode

def decide(obs):
    cambios = [
        cambiar_comportamiento(jugador, BehaviourMode.DEFENSIVE)
        for jugador in obs.players_id
    ]
    if obs.can_substitute:
        cambio = sustituir(obs.players_id[0], obs.substitutes_id[0])
        return DtAction(cambios, [cambio])
    return DtAction(cambios)`;

const dtApiFunctions = [
    { name: 'obs.time_played', description: 'Tiempo de juego transcurrido en segundos.' },
    { name: 'obs.my_goals / obs.rival_goals', description: 'Goles de tu equipo y del rival.' },
    { name: 'obs.players_id / obs.substitutes_id', description: 'Identificadores de los jugadores en cancha y del banco.' },
    { name: 'obs.can_substitute', description: 'Indica que el DT puede pedir una sustitución en la pausa actual.' },
    { name: 'obs.pause_index', description: 'Vale 1, 2 o 3 durante una pausa. El 2 corresponde al entretiempo.' },
    { name: 'cambiar_comportamiento(jugador, modo)', description: 'Acepta BehaviourMode.BALANCED, BehaviourMode.OFFENSIVE y BehaviourMode.DEFENSIVE.' },
    { name: 'sustituir(titular, suplente)', description: 'Pide un cambio durante una pausa con cuota disponible.' },
    { name: 'DtAction(cambios, sustituciones)', description: 'Devuelve las órdenes que evaluará el motor. La lista de sustituciones es opcional.' },
];

const playerApiFunctions = [
        { name: 'tiempo_jugado()', description: 'Devuelve el tiempo de juego transcurrido.', returnType: 'Número' },
        { name: 'tiempo_restante()', description: 'Devuelve el tiempo de juego restante.', returnType: 'Número' },
        { name: 'vamos_ganando()', description: 'Indica si nuestro equipo está ganando.', returnType: 'bool' },
        { name: 'vamos_empatando()', description: 'Indica si ambos equipos están empatados.', returnType: 'bool' },
        { name: 'tengo_pelota()', description: 'Indica si el jugador actual tiene la posesión.', returnType: 'bool' },
        { name: 'equipo_tiene_pelota()', description: 'Indica si algún jugador de nuestro equipo tiene la posesión, incluido el actual.', returnType: 'bool' },
        { name: 'estamos_atacando()', description: 'Indica si nuestro equipo tiene la pelota en campo rival.', returnType: 'bool' },
        { name: 'estamos_defendiendo()', description: 'Indica si el rival tiene la pelota en nuestro campo.', returnType: 'bool' },
        { name: 'bajo_presion()', description: 'Indica si hay un rival cerca del jugador actual.', returnType: 'bool' },
        { name: 'pelota_en_nuestro_campo()', description: 'Indica si la pelota está en nuestra mitad de cancha.', returnType: 'bool' },
        { name: 'pelota_en_su_campo()', description: 'Indica si la pelota está en la mitad rival.', returnType: 'bool' },
        { name: 'pelota_libre()', description: 'Indica si ningún jugador tiene la pelota.', returnType: 'bool' },
        { name: 'puedo_patear()', description: 'Indica si la pelota está al alcance y terminó la espera entre patadas.', returnType: 'bool' },
        { name: 'mi_posicion()', description: 'Devuelve la posición actual del jugador.', returnType: 'Posición' },
        { name: 'posicion_pelota()', description: 'Devuelve la posición actual de la pelota.', returnType: 'Posición' },
        { name: 'posicion_base()', description: 'Devuelve la posición asignada al jugador según la formación.', returnType: 'Posición' },
        { name: 'arco_propio()', description: 'Devuelve el centro del arco propio.', returnType: 'Posición' },
        { name: 'arco_rival()', description: 'Devuelve el centro del arco rival.', returnType: 'Posición' },
        { name: 'compañeros()', description: 'Devuelve las posiciones de los compañeros, excluyendo al jugador actual.', returnType: 'Lista de posiciones' },
        { name: 'rivales()', description: 'Devuelve las posiciones de los jugadores rivales.', returnType: 'Lista de posiciones' },
        { name: 'compañero_mas_cercano()', description: 'Devuelve la posición del compañero más cercano, o None si no hay.', returnType: 'Posición | None' },
        { name: 'rival_mas_cercano()', description: 'Devuelve la posición del rival más cercano, o None si no hay.', returnType: 'Posición | None' },
        { name: 'patear_a(direccion)', description: 'Intenta patear hacia la dirección indicada.', returnType: 'Command' },
        { name: 'ir_a(direccion)', description: 'Ordena desplazarse hacia la dirección indicada.', returnType: 'Command' },
        { name: 'ir_a_pelota()', description: 'Ordena acercarse a la pelota.', returnType: 'Command' },
        { name: 'quedarse(posicion)', description: 'Ordena desplazarse a la posición indicada.', returnType: 'Command' },
        { name: 'cubrir_arco()', description: 'Busca ubicarse entre la pelota y el arco propio.', returnType: 'Command' },
        { name: 'conducir_hacia(direccion)', description: 'Intenta avanzar hacia una dirección acompañando la pelota.', returnType: 'Command' },
];

export default function CreateBehaviourPage({ kind = 'PLAYER' }) {
    const isDt = kind === 'DT';
    const template = isDt ? DT_TEMPLATE : PLAYER_TEMPLATE;
    const apiFunctions = isDt ? dtApiFunctions : playerApiFunctions;
    const [name, setName] = useState('');
    const [code, setCode] = useState(isDt ? template : '');
    const [error, setError] = useState('');
    const [diagnostics, setDiagnostics] = useState([]);
    const [isValid, setIsValid] = useState(false);
    const [action, setAction] = useState('');
    const navigate = useNavigate();

    function clearFeedback() {
        setError('');
        setDiagnostics([]);
        setIsValid(false);
    }

    async function handleValidate() {
        if (action || !code.trim()) return;
        clearFeedback();
        setAction('validate');
        try {
            const result = await validateBehaviour(isDt ? 'COACH' : 'PLAYER', code);
            setIsValid(result.valid);
            setDiagnostics(result.diagnostics);
            if (!result.valid) setError('Revisá el código antes de guardarlo.');
        } catch (err) {
            setError(err.message || 'No se pudo validar el comportamiento.');
        } finally {
            setAction('');
        }
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (action) return;
        clearFeedback();

        if (!name.trim() || !code.trim()) {
            setError('Deben completarse todos los campos.');
            return;
        }

        setAction('save');
        try {
            if (isDt) {
                await createDtBehaviour(name.trim(), code);
                navigate('/mi-club', {
                    replace: true,
                    state: { tab: 'dt', notice: 'Comportamiento del DT creado. Ya podés seleccionarlo y guardar el DT.' },
                });
            } else {
                await createBehaviour(name, code);
                navigate('/behaviours', { replace: true });
            }
        } catch (err) {
            const fields = Object.values(err.fields || {});
            setError(
                fields.join(' ') || err.message || 'No se pudo crear el comportamiento.'
            );
            setDiagnostics(err.diagnostics ?? []);
        } finally {
            setAction('');
        }
    }

    return (
        <div className="max-w-4xl mx-auto p-6 flex flex-col">
            {isDt && <Link to="/mi-club" state={{tab: 'dt'}} className="mb-4 text-sm underline">Volver a Mi club</Link>}
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
                        defaultValue=""
                        disabled={Boolean(action)}
                        className="w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
                    <Editor
                        height="300px"
                        width="100%"
                        defaultLanguage="python"
                        defaultValue={template}
                        theme="vs-dark"
                        options={{ readOnly: Boolean(action), ariaLabel: 'Código del comportamiento' }}
                        onChange={(value) => {
                            setCode(value ?? '');
                            clearFeedback();
                        }}
                    />

                    <aside
                        aria-label="Funciones disponibles de la API"
                        className="max-h-[300px] overflow-y-auto overscroll-contain rounded-lg border border-gray-300 bg-white p-4"
                    >
                        <h3 className="mb-3 font-semibold">Funciones disponibles</h3>

                        <ul className="space-y-3">
                            {apiFunctions.map((fn) => (
                                <li key={fn.name} className="text-sm">
                                    <code className="font-semibold text-blue-700">{fn.name}</code>
                                    <p className="text-gray-600">{fn.description}</p>
                                </li>
                            ))}
                        </ul>
                    </aside>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                    <Button type="button" variant="outline" onClick={handleValidate} disabled={Boolean(action) || !code.trim()}>
                        {action === 'validate' ? 'Validando…' : 'Validar código'}
                    </Button>
                    <Button type="submit" disabled={Boolean(action)}>
                        {action === 'save' ? 'Guardando…' : 'Guardar Comportamiento'}
                    </Button>
                </div>

                {error && (
                    <div role="alert" className="text-destructive">
                        <p>{error}</p>
                        {diagnostics.length > 0 && (
                            <ul className="list-disc pl-5">
                                {diagnostics.map((item, index) => (
                                    <li key={index}>{item.line > 0 && `Línea ${item.line} · `}{item.message}</li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}

                {isValid && <p role="status">El código es válido.</p>}
            </form>
        </div>
    );
}
