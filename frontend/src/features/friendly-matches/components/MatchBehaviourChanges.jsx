import {useState} from 'react';
import { changeBehaviour } from '../matchApi';
import '../MatchPage.css'

function PlayerBehaviourSelector({matchId, player, behaviours, canChange}) {
    const [sending, setSending] = useState(false);
    const [error, setError] = useState('');
    const confirmedId = String(player.behaviourId ?? '');
    const confirmedBehaviour = behaviours.find(({id}) => String(id) === confirmedId);
    const confirmedName = confirmedBehaviour?.name ?? player.behaviourName ?? 'Sin identificar';

    async function handleChange(event) {
        const behaviourId = event.target.value;
        if (!canChange || sending || !behaviourId || behaviourId === confirmedId) return;

        setSending(true);
        setError('');
        try {
            await changeBehaviour(matchId, player.id, Number(behaviourId));
        } catch (requestError) {
            setError(requestError.message || 'No se pudo enviar la orden.');
        } finally {
            setSending(false);
        }
    }

    return (
        <>
            <p className="mt-2">
                <span className="font-medium">Comportamiento actual:</span>{' '}
                {confirmedName}
            </p>
            <div className="mt-2">
                <select
                    aria-label={`Cambiar táctica de ${player.name} (#${player.id})`}
                    className="w-full text-sm p-1 border rounded"
                    value={confirmedId}
                    disabled={!canChange || sending || behaviours.length === 0}
                    onChange={handleChange}
                >
                    {!confirmedBehaviour && <option value={confirmedId} disabled>{confirmedName}</option>}
                    {behaviours.map(({id, name}) => <option key={id} value={id}>{name}</option>)}
                </select>
                {sending && <p role="status" className="mt-1 text-xs text-muted-foreground">Enviando orden…</p>}
                {error && <p role="alert" className="mt-1 text-xs text-destructive">{error}</p>}
            </div>
        </>
    );
}

export default function LiveChangeBehaviour({matchId, players, behaviours, isMyTeam, canChange}) {
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
                                    <PlayerBehaviourSelector
                                        matchId={matchId}
                                        player={player}
                                        behaviours={behaviours}
                                        canChange={canChange}
                                    />
                                ) : (
                                    <p className="text-xs text-gray-400 mt-1 italic">Oculto</p>
                                )}
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
