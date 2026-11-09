import {useEffect, useRef, useState} from 'react';
import {ArrowLeft, ChartNoAxesColumnIncreasing, CircleAlert, Shirt, Trophy, Users} from 'lucide-react';
import {Link, useParams} from 'react-router';
import {toast} from 'sonner';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardContent, CardDescription, CardHeader} from '@/components/ui/card';
import {Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle} from '@/components/ui/empty';
import {Item, ItemContent, ItemMedia} from '@/components/ui/item';
import {Skeleton} from '@/components/ui/skeleton';
import {routes} from '@/routes.js';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {getClubProfile} from './api.js';

const LOAD_ERROR_TITLE = 'No se pudo cargar el club';
const METRIC_CLASSES = 'min-w-0 rounded-lg border bg-muted/40 p-3';

const STAT_FIELDS = [
    ['played', 'Partidos jugados'],
    ['wins', 'Victorias'],
    ['draws', 'Empates'],
    ['losses', 'Derrotas'],
];

function profileErrorMessage(error) {
    if (error.status === 404) return 'El club solicitado no existe.';
    if (error.status === 401) return 'Iniciá sesión para consultar este club.';
    if (error.status === 0) return 'No se pudo conectar con el servidor.';
    return error.message || 'Intentá nuevamente.';
}

export default function ClubProfilePage() {
    const {clubId} = useParams();

    return <ClubProfileContent key={clubId} clubId={clubId}/>;
}

function ClubProfileContent({clubId}) {
    const [attempt, setAttempt] = useState(0);
    const [state, setState] = useState({status: 'loading'});
    const retryToast = useRef(null);

    useEffect(() => {
        const controller = new AbortController();

        async function loadClub() {
            try {
                const club = await getClubProfile(clubId, {signal: controller.signal});
                if (!controller.signal.aborted) setState({status: 'success', club});
            } catch (error) {
                if (controller.signal.aborted || error.name === 'AbortError') return;

                setState({status: 'error', error});
                if (attempt > 0 && error.status !== 401 && error.status !== 404) {
                    retryToast.current = toast.error(LOAD_ERROR_TITLE, {description: profileErrorMessage(error)});
                }
            }
        }

        loadClub();
        return () => controller.abort();
    }, [clubId, attempt]);

    function handleRetry() {
        if (retryToast.current !== null) {
            toast.dismiss(retryToast.current);
            retryToast.current = null;
        }
        setState({status: 'loading'});
        setAttempt(value => value + 1);
    }

    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
            <Link to={routes.clubs} className={buttonVariants({variant: 'ghost'})}>
                <ArrowLeft data-icon="inline-start" aria-hidden="true"/>
                Volver a clubes
            </Link>

            {state.status === 'loading' && (
                <div role="status">
                    <span className="sr-only">Cargando club…</span>
                    <div className="space-y-6" aria-hidden="true">
                        <Skeleton className="h-28 w-full rounded-xl"/>
                        <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
                            <Skeleton className="h-44 w-full rounded-xl"/>
                            <Skeleton className="h-44 w-full rounded-xl"/>
                        </div>
                        <Skeleton className="h-40 w-full rounded-xl"/>
                    </div>
                </div>
            )}

            {state.status === 'error' && <ClubProfileError error={state.error} onRetry={handleRetry}/>}
            {state.status === 'success' && <ClubProfileDetails club={state.club}/>}
        </main>
    );
}

function ClubProfileError({error, onRetry}) {
    const isNotFound = error.status === 404;
    const isSessionError = error.status === 401;

    return (
        <Alert variant="destructive">
            <CircleAlert aria-hidden="true"/>
            <AlertTitle>
                <h1 className="font-semibold">{isNotFound ? 'Club no encontrado' : LOAD_ERROR_TITLE}</h1>
            </AlertTitle>
            <AlertDescription>{profileErrorMessage(error)}</AlertDescription>
            {!isNotFound && (
                <div className="col-start-2 pt-2">
                    {isSessionError ? (
                        <Link to={routes.signIn} className={buttonVariants({variant: 'outline'})}>
                            Iniciar sesión
                        </Link>
                    ) : (
                        <Button type="button" variant="outline" onClick={onRetry}>Reintentar</Button>
                    )}
                </div>
            )}
        </Alert>
    );
}

function ClubProfileDetails({club}) {
    return (
        <>
            <Card>
                <CardContent className="flex items-center gap-4">
                    <ClubAvatar avatar={club.avatar} clubName={club.name}/>
                    <div className="min-w-0 space-y-1">
                        <p className="text-xs font-bold tracking-[0.12em] text-muted-foreground uppercase">
                            Perfil público
                        </p>
                        <h1 className="text-2xl font-bold wrap-anywhere sm:text-3xl">{club.name}</h1>
                    </div>
                </CardContent>
            </Card>

            <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
                <section aria-labelledby="club-stats-title" className="min-w-0">
                    <Card className="h-full">
                        <CardHeader>
                            <h2 id="club-stats-title" className="flex items-center gap-2 text-lg font-bold">
                                <ChartNoAxesColumnIncreasing className="size-5 text-primary" aria-hidden="true"/>
                                Estadísticas
                            </h2>
                            <CardDescription>Resultados acumulados del club.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                                {STAT_FIELDS.map(([field, label]) => (
                                    <div key={field} className={METRIC_CLASSES}>
                                        <dt className="text-sm text-muted-foreground">{label}</dt>
                                        <dd className="mt-1 text-2xl font-bold tabular-nums">{club.stats[field]}</dd>
                                    </div>
                                ))}
                            </dl>
                        </CardContent>
                    </Card>
                </section>

                <section aria-labelledby="club-ranking-title" className="min-w-0">
                    <Card className="h-full">
                        <CardHeader>
                            <h2 id="club-ranking-title" className="flex items-center gap-2 text-lg font-bold">
                                <Trophy className="size-5 text-primary" aria-hidden="true"/>
                                Ranking global
                            </h2>
                            <CardDescription>Solo resultados de ligas públicas.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <dl className="grid grid-cols-2 gap-3">
                                <div className={METRIC_CLASSES}>
                                    <dt className="text-sm text-muted-foreground">Posición</dt>
                                    <dd className="mt-1 text-2xl font-bold text-primary tabular-nums">
                                        {club.ranking.position}
                                    </dd>
                                </div>
                                <div className={METRIC_CLASSES}>
                                    <dt className="text-sm text-muted-foreground">Puntos</dt>
                                    <dd className="mt-1 text-2xl font-bold tabular-nums">{club.ranking.points}</dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>
                </section>
            </div>

            <section aria-labelledby="club-players-title">
                <Card>
                    <CardHeader className="flex flex-wrap items-center justify-between gap-2">
                        <h2 id="club-players-title" className="flex items-center gap-2 text-lg font-bold">
                            <Users className="size-5 text-primary" aria-hidden="true"/>
                            Plantilla
                        </h2>
                        <Badge variant="secondary">
                            {club.players.length} {club.players.length === 1 ? 'jugador' : 'jugadores'}
                        </Badge>
                    </CardHeader>
                    <CardContent>
                        {club.players.length === 0 ? (
                            <Empty className="border">
                                <EmptyHeader>
                                    <EmptyMedia variant="icon"><Users aria-hidden="true"/></EmptyMedia>
                                    <EmptyTitle>Sin jugadores</EmptyTitle>
                                    <EmptyDescription>Este club todavía no tiene jugadores.</EmptyDescription>
                                </EmptyHeader>
                            </Empty>
                        ) : (
                            <ul className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3" aria-label="Jugadores del club">
                                {club.players.map(player => (
                                    <Item key={player.id} render={<li/>} variant="outline" className="flex-nowrap">
                                        <ItemMedia
                                            className="size-8 rounded-lg bg-primary/10 text-primary"
                                            variant="icon"
                                            aria-hidden="true"
                                        >
                                            <Shirt/>
                                        </ItemMedia>
                                        <ItemContent className="min-w-0">
                                            <span className="font-medium wrap-anywhere">{player.name}</span>
                                        </ItemContent>
                                    </Item>
                                ))}
                            </ul>
                        )}
                    </CardContent>
                </Card>
            </section>
        </>
    );
}
