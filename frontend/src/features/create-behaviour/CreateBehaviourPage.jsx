import Editor from "@monaco-editor/react";
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { createBehaviour } from './api';
import BehaviourCodeEditor from '../behaviours/components/BehaviourCodeEditor';
import {useUnsavedChanges} from '../behaviours/hooks/useUnsavedChanges';

const DEFAULT_CODE = 'def decide(observation):\n    return ir_a_pelota()\n';

export default function CreateBehaviourPage() {
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();
    const [code, setCode] = useState(DEFAULT_CODE);
    const [diagnostics, setDiagnostics] = useState([]);
    const [isSaving, setIsSaving] = useState(false);
    const pending = useRef(false);

    const allowNavigation = useUnsavedChanges(name !== '' || code !== DEFAULT_CODE);
    const apiFunctions = [
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


    async function handleSubmit(event) {
        event.preventDefault();
        if (pending.current) return;

        setError('');
        setSuccess('');
        setDiagnostics([]);

        if (!name.trim() || !code.trim()) {
            setError('Deben completarse todos los campos.');
            return;
        }
        pending.current = true;
        setIsSaving(true);

        try {
            await createBehaviour(name, code);
            allowNavigation();
            navigate('/behaviours', {
                replace: true,
                state: {
                    notice: 'Comportamiento creado exitosamente.',
                },
            });
        } catch (err) {
            setDiagnostics(err.diagnostics ?? []);

            const fields = Object.values(err.fields ?? {});
            setError(
                fields.join(' ') ||
                err.message ||
                'No se pudo crear el comportamiento.'
            );
        } finally {
            pending.current = false;
            setIsSaving(false);
        }
    }    
    return (
        <div className="max-w-4xl mx-auto p-6 flex flex-col">
            <h2 className="text-2xl font-bold mb-6 text-gray-800 ">Crear Comportamiento</h2>
            <form onSubmit={handleSubmit} className="w-full space-y-4">
                <div>
                    <input
                        type="text"
                        placeholder="Ingrese el nombre"
                        value={name}
                        readOnly={isSaving}
                        className="w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <BehaviourCodeEditor
                    value={code}
                    onChange={(value) => {
                        setCode(value);
                        setDiagnostics([]);
                    }}
                    diagnostics={diagnostics}
                    documentId="new"
                    kind="PLAYER"
                    readOnly={isSaving}
                />
                <button
                    type="submit"
                    className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow"
                    disabled={isSaving}
                >
                    {isSaving ? 'Guardando…' : 'Guardar Comportamiento'}
                </button>

                {error && (
                    <p role="alert">
                        {error}
                    </p>
                )}

                {success && (
                    <p role="status">
                        {success}
                    </p>
                )}
            </form>
        </div>
    );
} 