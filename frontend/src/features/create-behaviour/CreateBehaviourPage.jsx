import Editor from "@monaco-editor/react";
import { useState } from 'react';
import { createBehaviour } from './api';

export default function CreateBehaviourPage() {
    const [name, setName] = useState('');
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');


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
                <div>
                    <Editor
                        height="300px"
                        width="100%"
                        defaultLanguage="python"
                        defaultValue="# Escribe tu código aquí"
                        theme="vs-dark"
                        onChange={(value) => setCode(value)}
                    />
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