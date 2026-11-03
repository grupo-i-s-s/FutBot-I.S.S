import Editor from "@monaco-editor/react";

export default function CreateBehaviourPage() {
    const handleEditorChange = (value, event) => {
        console.log("Código del usuario:", value);
    };

    return (
        <div className="max-w-4xl mx-auto p-6 flex flex-col items-center">
            <h2 className="text-2xl font-bold mb-6 text-gray-800 text-center">Crear Comportamiento</h2>
            <form onSubmit={(e) => e.preventDefault()} className="w-full space-y-4">
                <div>
                    <input
                        type="text"
                        placeholder="Ingrese el nombre"
                        defaultValue=""
                        className="w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                    />
                </div>
                <div>
                    <Editor
                        height="300px"
                        width="100%"
                        defaultLanguage="python"
                        defaultValue="# Escribe tu código aquí"
                        theme="vs-dark"
                        onChange={handleEditorChange}
                    />
                </div>
                <button
                    type="submit"
                    className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow"
                >
                    Guardar Comportamiento
                </button>
            </form>
        </div>
    );
} 