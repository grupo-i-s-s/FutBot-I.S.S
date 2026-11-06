import Editor from "@monaco-editor/react";
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { createBehaviour } from './api';

export default function CreateBehaviourPage() {
    const [name, setName] = useState('');
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

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
        setError('');
        setSuccess('');

        if (!name.trim() || !code.trim()) {
            setError('Deben completarse todos los campos.');
            return;
        }

        try {
            await createBehaviour(name, code);
            setSuccess('Comportamiento creado exitosamente.');
            navigate('/behaviours', { replace: true });
        } catch (err) {
            const fields = Object.values(err.fields || {});
            setError(
                fields.join(' ') || err.message || 'No se pudo crear el comportamiento.'
            );
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
                        defaultValue=""
                        className="w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
                    <Editor
                        height="300px"
                        width="100%"
                        defaultLanguage="python"
                        defaultValue={`def decide(observation):
    #return ir_a_pelota()`}
                        theme="vs-dark"
                        onChange={(value) => setCode(value ?? '')}
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
                <button
                    type="submit"
                    className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow"
                >
                    Guardar Comportamiento
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