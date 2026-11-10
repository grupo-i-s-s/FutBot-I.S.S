import {Users} from 'lucide-react';

export default function MatchBench({teamName, players}) {
    if (!players) return null;

    return (
        <section aria-label={`Banco de ${teamName}`} className="space-y-3 border-t pt-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
                <Users className="size-4 text-primary" aria-hidden="true"/>
                Banco de suplentes <span className="text-xs font-normal text-muted-foreground">({players.length})</span>
            </h3>
            {players.length > 0 ? (
                <ul className="flex list-none flex-wrap gap-2 p-0">
                    {players.map(player => (
                        <li key={player.playerId} className="inline-flex max-w-full items-center gap-2 rounded-lg border bg-secondary/50 px-3 py-2 text-xs">
                            <span className="shrink-0 text-muted-foreground">#{player.playerId}</span>
                            <span className="font-medium wrap-anywhere">{player.name}</span>
                        </li>
                    ))}
                </ul>
            ) : <p className="text-xs text-muted-foreground">Sin suplentes en este partido.</p>}
        </section>
    );
}
