import Editor from "@monaco-editor/react";

export default function CreateBehaviourPage() {
    const handleEditorChange = (value, event) => {
        console.log("Código del usuario:", value);
    };

    return (
        <div className="flex justify-center">
            <Editor
                height="500px"
                width="50%"
                center
                defaultLanguage="python"
                defaultValue="# Escribe tu código aquí"
                theme="vs-dark"
                onChange={handleEditorChange}
            />
        </div>
    );
} 