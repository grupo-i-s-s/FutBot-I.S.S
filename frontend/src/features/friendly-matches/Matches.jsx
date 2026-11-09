import {useState} from 'react';
import {CalendarDays, CircleAlert, LogIn, Plus, RefreshCw, Swords} from 'lucide-react';
import {Link, useLocation, useNavigate} from 'react-router';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Avatar, AvatarFallback} from '@/components/ui/avatar';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardContent} from '@/components/ui/card';
import {Empty, EmptyHeader, EmptyMedia, EmptyTitle} from '@/components/ui/empty';
import {Item, ItemActions, ItemContent, ItemDescription, ItemMedia, ItemTitle} from '@/components/ui/item';
import {Skeleton} from '@/components/ui/skeleton';
import {routePath, routes} from '@/routes.js';
import {joinFriendlyMatch} from './api.js';
import FriendlyMatchSearch, {FriendlyMatchPagination} from './components/FriendlyMatchSearch.jsx';
import {useFriendlyMatches} from './hooks/useFriendlyMatches.js';
import {friendlyMatchError} from './scheduleConflict.js';

export default function MatchesPage() {
    const [joinError, setJoinError] = useState('');
    const [joiningId, setJoiningId] = useState(null);
    const search = useFriendlyMatches();
    const navigate = useNavigate();
    const location = useLocation();
    const returnTo = location.pathname + location.search + location.hash;
    const joining = joiningId !== null;
    const {items, total} = search.result;

    async function handleJoinMatch(matchId) {
        if (joining) return;

        setJoiningId(matchId);
        setJoinError('');
        try {
            const response = await joinFriendlyMatch(matchId);
            navigate(routePath(routes.match, {matchId: response.matchId}), {state: {returnTo}});
        } catch (error) {
            setJoinError(friendlyMatchError(error, 'No se pudo completar la inscripción al partido.'));
            search.reload();
        } finally {
            setJoiningId(null);
        }
    }

    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
            <Card>
                <CardContent className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-4">
                        <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                            <Swords className="size-6" aria-hidden="true"/>
                        </span>
                        <div className="space-y-1">
                            <h1 className="text-2xl font-bold sm:text-3xl">Amistosos</h1>
                            <p className="text-muted-foreground">Buscá un rival para tu club o creá un partido.</p>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <Link
                            to={{pathname: routes.myClub, search: '?tab=amistosos'}}
                            className={buttonVariants({variant: 'outline', size: 'lg'})}
                        >
                            Mis amistosos
                        </Link>
                        <Link to={routes.createMatch} className={buttonVariants({size: 'lg'})}>
                            <Plus data-icon="inline-start" aria-hidden="true"/>
                            Crear amistoso
                        </Link>
                    </div>
                </CardContent>
            </Card>

            <section aria-labelledby="available-matches-title">
                <Card>
                    <CardContent className="space-y-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <h2 id="available-matches-title" className="text-lg font-bold">Amistosos disponibles</h2>
                            <Button type="button" variant="outline" disabled={search.loading || joining}
                                    onClick={search.reload}>
                                <RefreshCw data-icon="inline-start" aria-hidden="true"/>
                                Actualizar
                            </Button>
                        </div>
                        <FriendlyMatchSearch search={search} disabled={joining}/>

                        {joinError && (
                            <Alert variant="destructive">
                                <CircleAlert aria-hidden="true"/>
                                <AlertTitle>No pudiste unirte al partido</AlertTitle>
                                <AlertDescription>{joinError}</AlertDescription>
                            </Alert>
                        )}

                        {search.loading && (
                            <div role="status">
                                <span className="sr-only">Buscando amistosos…</span>
                                <div className="space-y-2.5" aria-hidden="true">
                                    <Skeleton className="h-16 w-full"/>
                                    <Skeleton className="h-16 w-full"/>
                                    <Skeleton className="h-16 w-full"/>
                                </div>
                            </div>
                        )}

                        {search.error && (
                            <Alert variant="destructive">
                                <CircleAlert aria-hidden="true"/>
                                <AlertTitle>No se pudieron cargar los amistosos</AlertTitle>
                                <AlertDescription>{search.error}</AlertDescription>
                                <div className="col-start-2 pt-2">
                                    <Button type="button" variant="outline" onClick={search.reload}>Reintentar búsqueda</Button>
                                </div>
                            </Alert>
                        )}

                        {!search.loading && !search.error && (
                            items.length === 0 ? (
                                <Empty className="border" role="status">
                                    <EmptyHeader>
                                        <EmptyMedia variant="icon"><Swords aria-hidden="true"/></EmptyMedia>
                                        <EmptyTitle>{total > 0 ? 'No hay partidos en esta página.'
                                            : search.creatorName ? `No se encontraron amistosos para "${search.creatorName}".`
                                                : 'No hay partidos disponibles.'}</EmptyTitle>
                                    </EmptyHeader>
                                </Empty>
                            ) : (
                                <ul className="space-y-2.5" aria-label="Resultados de amistosos">
                                    {items.map(match => (
                                        <Item key={match.matchId} render={<li/>} variant="outline" className="flex-nowrap gap-3">
                                            <ItemMedia aria-hidden="true">
                                                <Avatar size="lg">
                                                    <AvatarFallback className="bg-primary/10 font-semibold text-primary">
                                                        {match.creatorClubName.charAt(0).toLocaleUpperCase('es-AR')}
                                                    </AvatarFallback>
                                                </Avatar>
                                            </ItemMedia>
                                            <ItemContent className="min-w-0">
                                                <ItemTitle id={`friendly-club-${match.matchId}`}
                                                           className="line-clamp-none font-semibold wrap-anywhere">
                                                    {match.creatorClubName}
                                                </ItemTitle>
                                                <ItemDescription className="flex items-center gap-1.5">
                                                    <CalendarDays className="size-3.5 shrink-0" aria-hidden="true"/>
                                                    <time dateTime={match.startDateTime}>
                                                        {new Date(match.startDateTime).toLocaleString('es-AR', {
                                                            dateStyle: 'medium', timeStyle: 'short',
                                                        })}
                                                    </time>
                                                </ItemDescription>
                                            </ItemContent>
                                            <ItemActions>
                                                <Button type="button" size="lg" disabled={joining}
                                                        aria-describedby={`friendly-club-${match.matchId}`}
                                                        onClick={() => handleJoinMatch(match.matchId)}>
                                                    <LogIn data-icon="inline-start" aria-hidden="true"/>
                                                    {joiningId === match.matchId ? 'Uniéndose…' : 'Unirse'}
                                                </Button>
                                            </ItemActions>
                                        </Item>
                                    ))}
                                </ul>
                            )
                        )}

                        {!search.error && <FriendlyMatchPagination search={search} disabled={joining}/>}
                    </CardContent>
                </Card>
            </section>
        </main>
    );
}
