import {useState} from 'react';
import { changeBehaviour } from '../matchApi';
import {UserRound} from 'lucide-react';

const modeNames = {
    BALANCED: 'Equilibrado',
    OFFENSIVE: 'Ofensivo',
    DEFENSIVE: 'Defensivo',
    CUSTOM: 'Personalizado',
};

function PlayerBehaviour({matchId, player, behaviours, allowManualActions, canChange}) {
    const [sending, setSending] = useState(false);
    const [error, setError] = useState('');
    const confirmedId = String(player.behaviourId ?? '');
    const confirmedBehaviour = behaviours.find(({id}) => String(id) === confirmedId);
    const confirmedName = confirmedBehaviour?.name ?? player.behaviourName
        ?? modeNames[player.behaviourMode] ?? 'Sin identificar';

    async function handleChange(event) {
        const behaviourId = event.target.value;
        if (!allowManualActions || !canChange || sending || !behaviourId || behaviourId === confirmedId) return;

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
            <p className="mt-1.5 text-xs leading-normal">
                <span className="text-muted-foreground">Comportamiento actual:</span>{' '}
                <span className="font-medium text-primary">{confirmedName}</span>
            </p>
            {allowManualActions && <div className="mt-1.5">
                <select
                    aria-label={`Cambiar táctica de ${player.name} (#${player.id})`}
                    className="h-8 w-full min-w-0 rounded-md border border-input bg-background px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-60"
                    value={confirmedId}
                    disabled={!canChange || sending || behaviours.length === 0}
                    onChange={handleChange}
                >
                    {!confirmedBehaviour && <option value={confirmedId} disabled>{confirmedName}</option>}
                    {behaviours.map(({id, name}) => <option key={id} value={id}>{name}</option>)}
                </select>
                {sending && <p role="status" className="mt-1 text-xs text-muted-foreground">Enviando orden…</p>}
                {error && <p role="alert" className="mt-1 text-xs text-destructive">{error}</p>}
            </div>}
        </>
    );
}

export default function LiveChangeBehaviour({matchId, players, behaviours, isMyTeam, allowManualActions, canChange}) {
    return (
        <ul className="grid list-none gap-1.5 p-0">
            {players.map(player => (
                <li key={player.id} className="min-w-0 rounded-lg border bg-background p-2">
                    <div className="flex min-w-0 items-center gap-2">
                        <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-secondary text-primary" aria-hidden="true">
                            <UserRound className="size-3.5"/>
                        </span>
                        <h4 className="min-w-0 text-xs font-semibold wrap-anywhere">#{player.id} {player.name}</h4>
                    </div>
                    {isMyTeam ? (
                        <PlayerBehaviour matchId={matchId} player={player} behaviours={behaviours}
                            allowManualActions={allowManualActions} canChange={canChange}/>
                    ) : <p className="mt-1.5 text-xs text-muted-foreground">Oculto</p>}
                </li>
            ))}
        </ul>
    );
}
