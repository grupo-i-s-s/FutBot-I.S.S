import {useEffect, useState} from 'react';
import Editor from '@monaco-editor/react';

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

export default function BehaviourCodeEditor({
    value,
    onChange,
    diagnostics = [],
    documentId = 'new',
    kind = 'PLAYER',
    readOnly = false,
}) {
    const [editor, setEditor] = useState(null);

    useEffect(() => {
        if (!editor) return;

        const model = editor.instance.getModel();
        if (!model) return;

        editor.monaco.editor.setModelMarkers(
            model,
            'futbot-behaviour',
            diagnostics.map((diagnostic) => ({
                severity: editor.monaco.MarkerSeverity.Error,
                message: `${diagnostic.code}: ${diagnostic.message}`,
                startLineNumber: diagnostic.line,
                startColumn: diagnostic.column,
                endLineNumber: diagnostic.line,
                endColumn: diagnostic.column + 1,
            }))
        );

        return () => {
            if (!model.isDisposed()) {
                editor.monaco.editor.setModelMarkers(
                    model,
                    'futbot-behaviour',
                    []
                );
            }
        };
    }, [editor, diagnostics]);

    function revealDiagnostic(diagnostic) {
        if (!editor) return;

        const position = {
            lineNumber: diagnostic.line,
            column: diagnostic.column,
        };

        editor.instance.revealPositionInCenter(position);
        editor.instance.setPosition(position);
        editor.instance.focus();
    }

    return (
        <div className="space-y-3">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
                <div className="min-w-0 overflow-hidden rounded-lg border">
                    <Editor
                        height="320px"
                        width="100%"
                        language="python"
                        path={`behaviours/${kind}/${documentId}.py`}
                        value={value}
                        theme="vs-dark"
                        loading={<p role="status">Cargando editor…</p>}
                        onChange={(code) => onChange(code ?? '')}
                        onMount={(instance, monaco) => {
                            setEditor({instance, monaco});
                        }}
                        options={{
                            ariaLabel: 'Código del comportamiento',
                            automaticLayout: true,
                            lineNumbers: 'on',
                            minimap: {enabled: false},
                            tabSize: 4,
                            insertSpaces: true,
                            scrollBeyondLastLine: false,
                            renderValidationDecorations: 'on',
                            readOnly,
                        }}
                    />
                </div>

                <aside
                    aria-label="Ayuda para escribir comportamientos"
                    className="max-h-80 overflow-y-auto rounded-lg border bg-white p-4"
                >
                    <h3 className="mb-2 font-semibold">
                        Observaciones y acciones
                    </h3>

                    <p className="mb-4 text-sm text-gray-600">
                        Escribí una función <code>decide(observation)</code>.
                        Consultá el estado del partido y devolvé una acción
                        válida. La validación se realiza en el servidor.
                    </p>

                    <ul className="space-y-3">
                        {apiFunctions.map((fn) => (
                            <li key={fn.name} className="text-sm">
                                <code className="font-semibold text-blue-700">
                                    {fn.name}
                                </code>
                                <p className="text-gray-600">
                                    {fn.description}
                                </p>
                            </li>
                        ))}
                    </ul>
                </aside>
            </div>

            {diagnostics.length > 0 && (
                <ul
                    aria-label="Diagnósticos del código"
                    className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3"
                >
                    {diagnostics.map((diagnostic, index) => (
                        <li key={`${diagnostic.line}-${diagnostic.column}-${index}`}>
                            <button
                                type="button"
                                className="text-left text-sm text-red-800 underline"
                                onClick={() => revealDiagnostic(diagnostic)}
                            >
                                Línea {diagnostic.line}, columna {diagnostic.column}:
                                {' '}{diagnostic.message}
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}