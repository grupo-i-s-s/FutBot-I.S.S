import {useEffect, useState} from 'react';
import {Link, useLocation} from 'react-router';
import {ArrowRight, CalendarDays, CircleAlert, RefreshCw, Swords} from 'lucide-react';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle} from '@/components/ui/empty';
import {Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemTitle} from '@/components/ui/item';
import {Skeleton} from '@/components/ui/skeleton';
import {routePath, routes} from '@/routes.js';
import {listMyFriendlyMatches} from '../../friendly-matches/api.js';

const MATCH_STATUSES = {
    WAITING: 'Esperando rival',
    WAITING_OPPONENT: 'Esperando rival',
    SCHEDULED: 'Programado',
    RUNNING: 'En juego',
    FINISHED: 'Finalizado',
    CANCELLED: 'Cancelado',
};

const STATUS_VARIANTS = {RUNNING: 'default', CANCELLED: 'destructive'};

export default function MyFriendlyMatches() {
    const {pathname, search, hash} = useLocation();
    const returnTo = pathname + search + hash;
    const [attempt, setAttempt] = useState(0);
    const [result, setResult] = useState({status: 'loading'});
    const loading = result.status === 'loading';

    useEffect(() => {
        const controller = new AbortController();

        async function loadMatches() {
            try {
                const matches = await listMyFriendlyMatches(controller.signal);
                if (!controller.signal.aborted) setResult({status: 'ready', matches});
            } catch (error) {
                if (!controller.signal.aborted) setResult({status: 'error', message: error.message});
            }
        }

        loadMatches();
        return () => controller.abort();
    }, [attempt]);

    function refresh() {
        setResult({status: 'loading'});
        setAttempt(value => value + 1);
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>
                    <h2 className="flex items-center gap-2 text-lg font-bold">
                        <Swords className="size-5" aria-hidden="true" />
                        Mis amistosos
                    </h2>
                </CardTitle>
                <CardDescription>Partidos que organizó tu club o a los que se unió.</CardDescription>
                <CardAction>
                    <Button type="button" variant="outline" size="sm" onClick={refresh} disabled={loading}>
                        <RefreshCw data-icon="inline-start" aria-hidden="true" />
                        {result.status === 'error' ? 'Reintentar' : 'Actualizar'}
                    </Button>
                </CardAction>
            </CardHeader>
            <CardContent>
                {loading && (
                    <div className="space-y-3" aria-busy="true">
                        <p className="sr-only" role="status">Cargando tus amistosos…</p>
                        <Skeleton className="h-16 rounded-lg" />
                        <Skeleton className="h-16 rounded-lg" />
                    </div>
                )}

                {result.status === 'error' && (
                    <Alert variant="destructive">
                        <CircleAlert aria-hidden="true" />
                        <AlertTitle>No se pudieron cargar tus amistosos</AlertTitle>
                        <AlertDescription>{result.message}</AlertDescription>
                    </Alert>
                )}

                {result.status === 'ready' && (result.matches.length === 0 ? (
                    <Empty className="border">
                        <EmptyHeader>
                            <EmptyMedia variant="icon"><Swords aria-hidden="true" /></EmptyMedia>
                            <EmptyTitle>Sin amistosos</EmptyTitle>
                            <EmptyDescription>Todavía no creaste ni te uniste a un amistoso.</EmptyDescription>
                        </EmptyHeader>
                        <EmptyContent>
                            <Link to={routes.friendlyMatches} className={buttonVariants()}>
                                Ver amistosos disponibles
                            </Link>
                        </EmptyContent>
                    </Empty>
                ) : (
                    <ItemGroup>
                        {result.matches.map((match) => (
                            <Item key={match.matchId} variant="outline" role="listitem">
                                <ItemContent className="min-w-0">
                                    <ItemTitle className="block wrap-break-word font-semibold">
                                        {match.creatorClubName}{match.visitorClubName && ` vs. ${match.visitorClubName}`}
                                    </ItemTitle>
                                    <ItemDescription className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                        <span className="inline-flex items-center gap-1.5">
                                            <CalendarDays className="size-4" aria-hidden="true" />
                                            <time dateTime={match.startDateTime}>
                                                {new Date(match.startDateTime).toLocaleString('es-AR', {dateStyle: 'medium', timeStyle: 'short'})}
                                            </time>
                                        </span>
                                        <span>{match.isCreator ? 'Creado por tu club' : 'Tu club es visitante'}</span>
                                    </ItemDescription>
                                </ItemContent>
                                <ItemActions className="flex-wrap">
                                    <Badge variant={STATUS_VARIANTS[match.status] ?? 'secondary'}>
                                        {MATCH_STATUSES[match.status] ?? match.status}
                                    </Badge>
                                    <Link
                                        to={routePath(routes.match, {matchId: match.matchId})}
                                        state={{returnTo}}
                                        className={buttonVariants({variant: 'outline', size: 'sm'})}
                                        aria-label={`Ver partido ${match.matchId}`}
                                    >
                                        Ver partido
                                        <ArrowRight data-icon="inline-end" aria-hidden="true" />
                                    </Link>
                                </ItemActions>
                            </Item>
                        ))}
                    </ItemGroup>
                ))}
            </CardContent>
        </Card>
    );
}
