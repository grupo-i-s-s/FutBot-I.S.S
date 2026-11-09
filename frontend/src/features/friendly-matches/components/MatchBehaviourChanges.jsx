import {useState} from 'react';
import { changeBehaviour } from '../matchApi';
import '../MatchPage.css';

const modeNames = {
    BALANCED: 'Equilibrado',
    OFFENSIVE: 'Ofensivo',
    DEFENSIVE: 'Defensivo',
    CUSTOM: 'Personalizado',
};

export default function LiveChangeBehaviour({ matchId, players, behaviours, isMyTeam, canEdit }) {
    const [pending, setPending] = useState({});
    const [errors, setErrors] = useState({});

    async function changeBehaviourHandler(playerId, behaviourId) {
        if (!isMyTeam || !canEdit || pending[playerId]) return;
        setPending(current => ({ ...current, [playerId]: true }));
        setErrors(current => ({ ...current, [playerId]: '' }));
        try {
            await changeBehaviour(matchId, playerId, Number(behaviourId));
        } catch (error) {
            setErrors(current => ({ ...current, [playerId]: error.message || 'No se pudo enviar el cambio.' }));
        } finally {
            setPending(current => ({ ...current, [playerId]: false }));
        }
    }

    return (
        <div>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {players.map((player) => {
                    const behaviour = behaviours.find(item => item.id === player.behaviourId);
                    const behaviourName = behaviour?.name ?? modeNames[player.behaviourMode] ?? 'Sin comportamiento';
                    return <li key={player.id}>
                        <div className="border rounded-lg p-3 shadow-sm bg-white flex items-center gap-3">
                            <div>
                                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center font-bold text-primary">
                                    {player.name.charAt(0).toUpperCase()}
                                </div>
                            </div>
                            <div className="min-w-0">
                                <h4 className="truncate">
                                    #{player.id} {player.name}
                                </h4>
                                {isMyTeam ? (
                                    <>
                                        <p className="mt-2">
                                            <span className="font-medium">Comportamiento actual:</span>{' '}
                                            {behaviourName}
                                        </p>

                                        <div className="mt-2">
                                            <select
                                                className="w-full text-sm p-1 border rounded"
                                                aria-label={`Comportamiento de ${player.name}`}
                                                value={behaviour?.id ?? ''}
                                                disabled={pending[player.id] || !canEdit || behaviours.length === 0}
                                                onChange={(e) => changeBehaviourHandler(player.id, e.target.value)}
                                            >
                                                <option value="" disabled>Cambiar táctica...</option>
                                                {behaviours.map(b => (
                                                    <option key={b.id} value={b.id}>{b.name}</option>
                                                ))}
                                            </select>
                                            
                                            {pending[player.id] && (
                                                <span className="text-xs text-gray-500 mt-1 block">Enviando orden...</span>
                                            )}
                                            {errors[player.id] && <p className="text-xs text-destructive" role="alert">{errors[player.id]}</p>}
                                        </div>
                                    </>
                                ) : (
                                    <p className = "text-xs text-gray-400 mt-1 italic"> Oculto </p>
                                )}
                            </div>
                        </div>
                    </li>;
                })}
            </ul>
        </div>
    );
}
