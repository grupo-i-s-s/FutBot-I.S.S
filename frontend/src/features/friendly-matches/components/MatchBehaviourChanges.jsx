import {useState} from 'react';
import { changeBehaviour } from '../matchApi';
import '../MatchPage.css'

export default function LiveChangeBehaviour({ match_id, players, behaviours, isMyTeam }) {
    const [change, setChange] = useState({});
    const [persistedBehaviour, setPersistedBehaviour] = useState({});

    const changeBehaviourHandler = async (playerId, behaviourId) => {

        setPersistedBehaviour(prev =>({...prev, [playerId]:behaviourId}));
        setChange(prev => ({...prev, [playerId]:true}));

        await changeBehaviour(match_id, playerId, Number(behaviourId));

        setChange(prev => ({...prev, [playerId]:false}));
    };

    return (
        <div>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {players.map((player) => (
                    <li key={player.id}>
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
                                            {player.behaviourName}
                                        </p>

                                        <div className="mt-2">
                                            <select
                                                className="w-full text-sm p-1 border rounded"
                                                value={persistedBehaviour[player.id] || player.behaviourId}
                                                disabled={change[player.id]}
                                                onChange={(e) => changeBehaviourHandler(player.id, e.target.value)}
                                            >
                                                <option value="" disabled>Cambiar táctica...</option>
                                                {behaviours.map(b => (
                                                    <option key={b.id} value={b.id}>{b.name}</option>
                                                ))}
                                            </select>
                                            
                                            {change[player.id] && (
                                                <span className="text-xs text-gray-500 mt-1 block">Enviando orden...</span>
                                            )}
                                        </div>
                                    </>
                                ) : (
                                    <p className = "text-xs text-gray-400 mt-1 italic"> Oculto </p>
                                )}
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}