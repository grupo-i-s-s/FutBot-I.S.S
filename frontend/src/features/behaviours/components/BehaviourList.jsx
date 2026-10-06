import React, {useEffect, useState} from 'react';
import {fetchBehaviours} from '../services/behavioursApi';

export default function BehaviourList() {
    const [behaviours, setBehaviours] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadBehaviours = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchBehaviours();
            setBehaviours(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadBehaviours();
    }, []);

    if (loading) {
        return <div className="p-6 text-center text-gray-600">Cargando catálogo de comportamientos...</div>;
    }

    if (error) {
        return (
            <div className="p-6 text-center text-red-600">
                <p className="mb-4">{error}</p>
                <button
                    onClick={loadBehaviours}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    if (behaviours.length === 0) {
        return <div className="p-6 text-center text-gray-500">No hay comportamientos disponibles en este momento.</div>;
    }

    return (
        <div className="max-w-4xl mx-auto p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Catálogo de Comportamientos</h2>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {behaviours.map((behaviour) => (
                    <li key={behaviour.id}
                        className="border p-4 rounded-lg shadow-sm bg-white flex flex-col justify-between">
                        <div>
                            <div className="flex justify-between items-start mb-2">
                                <h3 className="text-lg font-semibold text-gray-900">{behaviour.name}</h3>
                                {behaviour.isDefault && (
                                    <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded font-medium">
                    Default
                  </span>
                                )}
                            </div>
                            <p className="text-gray-600 text-sm mb-4">{behaviour.description || 'Sin descripción.'}</p>
                        </div>
                        <a
                            href={`/behaviours/${behaviour.id}`}
                            className="text-blue-600 hover:underline text-sm font-medium self-start"
                        >
                            Ver detalle &rarr;
                        </a>
                    </li>
                ))}
            </ul>
        </div>
    );
}
