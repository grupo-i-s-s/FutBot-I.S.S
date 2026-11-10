import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { abandonarLobby, iniciarLiga, obtenerIdentidad, obtenerLobby } from './api.js';
import LeagueRanking from './LeagueRanking.jsx';
import LeagueFixture from './LeagueFixture.jsx';
import {ArrowLeft, CircleAlert, ClipboardList, Play, RefreshCw, Trophy, Users} from 'lucide-react';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardContent, CardDescription, CardHeader} from '@/components/ui/card';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {routePath, routes} from '@/routes.js';

export function LeagueLobby() {
    const { id } = useParams();
    return <LeagueLobbyContent key={id} id={id} />;
}

function LeagueLobbyContent({ id }) {
    const [lobby, setLobby] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refresh, setRefresh] = useState(0);
    const [tab, setTab] = useState('lobby');
    const [clubId, setClubId] = useState(null);
    const [starting, setStarting] = useState(false);
    const [startError, setStartError] = useState('');
    const startingRef = useRef(false);
    const navigate = useNavigate();


    useEffect(() => {
        const controller = new AbortController();

        async function cargarLobby() {
            setLoading(true);
            setError(null);

            try {
                const [data, identity] = await Promise.all([
                    obtenerLobby(id, controller.signal),
                    obtenerIdentidad(controller.signal),
                ]);

                if (!controller.signal.aborted) {
                    setLobby(data);
                    setClubId(identity.clubId);
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(err);
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        cargarLobby();

        return () => controller.abort();
    }, [id, refresh]);

    useEffect(() => {
        function actualizar(event) {
            if (event.type === 'league-updated' && event.detail?.leagueId != null
                && String(event.detail.leagueId) !== id) return;
            if (!startingRef.current) setRefresh(value => value + 1);
        }
        window.addEventListener('focus', actualizar);
        window.addEventListener('league-updated', actualizar);
        return () => {
            window.removeEventListener('focus', actualizar);
            window.removeEventListener('league-updated', actualizar);
        };
    }, [id]);

    useEffect(() => {
        if (!['open', 'running'].includes(lobby?.status)) return;
        const timer = window.setInterval(() => {
            if (document.visibilityState === 'visible' && !startingRef.current) {
                setRefresh(value => value + 1);
            }
        }, 10000);
        return () => window.clearInterval(timer);
    }, [lobby?.status]);

    async function handleStartLeague() {
        if (startingRef.current) return;
        if (!window.confirm('Al iniciar se cierran las inscripciones y quedan programados los partidos. ¿Querés continuar?')) return;
        startingRef.current = true;
        setStarting(true);
        setStartError('');
        try {
            await iniciarLiga(id);
            setLobby(await obtenerLobby(id));
        } catch (err) {
            setStartError(err.message);
        } finally {
            startingRef.current = false;
            setStarting(false);
        }
    }

    async function handleLeaveLeague() {
        const isCreator = clubId === lobby?.creatorClubId;
        const message = isCreator
            ? '¿Seguro que querés cancelar esta liga? Esta acción no se puede deshacer.'
            : '¿Estás seguro de que querés abandonar esta liga?';

        if (!window.confirm(message)) return;

        try {
            await abandonarLobby(id);

            if (isCreator) {
                navigate(routes.home, {
                    replace: true,
                    state: { notice: 'La liga se ha eliminado.' },
                });
            } else {
                navigate(routes.myClub);
            }
        } catch (err) {
            alert(err.message || 'No se pudo abandonar la liga');
        }
    }

    if (loading && !lobby) {
        return <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl py-12">
            <Card><CardContent><p role="status" className="py-6 text-center text-muted-foreground">Cargando liga…</p></CardContent></Card>
        </main>;
    }

    if (error?.status === 404) {
        return <Navigate to={routes.cancelledLeague} replace />;
    }

    if (error && !lobby) {
        return <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-4 py-12">
            <Alert variant="destructive"><CircleAlert aria-hidden="true"/><AlertDescription>{error.message}</AlertDescription></Alert>
            {error.status === 401 ? (
                <Link to={routes.signIn} className={buttonVariants()}>Iniciar sesión</Link>
            ) : <Button type="button" variant="outline" onClick={() => setRefresh(value => value + 1)}>Reintentar</Button>}
            <Link to={routes.leagues} className={buttonVariants({variant: 'outline'})}>Volver a ligas disponibles</Link>
        </main>;
    }

    const started = lobby.status === 'running' || lobby.status === 'finished';
    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
            <Link to={routes.leagues} className={buttonVariants({variant: 'outline'})}>
                <ArrowLeft aria-hidden="true"/> Volver a ligas disponibles
            </Link>

            <header className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex min-w-0 items-center gap-4">
                    <span className="flex size-16 shrink-0 items-center justify-center rounded-2xl bg-secondary text-primary">
                        <Trophy className="size-8" aria-hidden="true"/>
                    </span>
                    <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2">
                        <h1 className="text-3xl font-bold tracking-tight wrap-anywhere sm:text-4xl">Liga {lobby.name}</h1>
                        <Badge variant="secondary" className="px-3 py-1 text-sm font-medium">{{open: 'Abierta', running: 'En curso', finished: 'Finalizada', cancelled: 'Cancelada'}[lobby.status] ?? lobby.status}</Badge>
                    </div>
                </div>
                <div className="flex flex-wrap gap-2">
                    <Button type="button" variant="outline" disabled={loading || starting} onClick={() => setRefresh(value => value + 1)}>
                        <RefreshCw className={loading ? 'animate-spin' : ''} aria-hidden="true"/> Actualizar
                    </Button>
                </div>
            </header>

            {error && <Alert variant="destructive"><CircleAlert aria-hidden="true"/><AlertDescription>{error.message}</AlertDescription></Alert>}

            <Tabs value={tab} onValueChange={setTab} className="gap-6">
                <div className="flex flex-wrap items-center justify-center gap-2 rounded-2xl border border-primary/15 bg-secondary/50 p-2">
                    <TabsList className="h-10 gap-2 bg-transparent p-0" aria-label="Vistas de la liga">
                        <TabsTrigger value="lobby" className="h-10 rounded-xl bg-primary/5 px-4 text-sm font-semibold text-primary hover:bg-primary/10 data-active:bg-primary/15 data-active:text-primary sm:px-5">
                            <ClipboardList aria-hidden="true"/> Lobby
                        </TabsTrigger>
                        <TabsTrigger value="ranking" className="h-10 rounded-xl bg-primary/5 px-4 text-sm font-semibold text-primary hover:bg-primary/10 data-active:bg-primary/15 data-active:text-primary sm:px-5">
                            <Trophy aria-hidden="true"/> Ranking
                        </TabsTrigger>
                    </TabsList>
                    {lobby.isRegistered && (
                        <Link to={routePath(routes.leagueLineup, {id})}
                            className={buttonVariants({variant: 'secondary', className: 'h-10 rounded-xl bg-primary/5 px-4 text-sm font-semibold text-primary hover:bg-primary/10 sm:px-5'})}>
                            <Users aria-hidden="true"/> Ver plantel
                        </Link>
                    )}
                </div>
                <TabsContent value="lobby" keepMounted className="space-y-6">
                    <Card>
                        <CardHeader><h2 className="text-lg font-bold">Detalles del Lobby</h2></CardHeader>
                        <CardContent>
                            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                                <div className="space-y-1 rounded-lg bg-muted/50 p-4">
                                    <dt className="text-sm text-muted-foreground">Tipo:</dt>
                                    <dd className="font-semibold">{lobby.isPrivate ? 'Privada' : 'Pública'}</dd>
                                </div>
                                <div className="space-y-1 rounded-lg bg-muted/50 p-4">
                                    <dt className="text-sm text-muted-foreground">Mínimo de clubes:</dt>
                                    <dd className="font-semibold">{lobby.minTeams}</dd>
                                </div>
                                <div className="space-y-1 rounded-lg bg-muted/50 p-4">
                                    <dt className="text-sm text-muted-foreground">Cupos restantes:</dt>
                                    <dd className="font-semibold">{lobby.remainingSlots}</dd>
                                </div>
                            </dl>
                        </CardContent>
                    </Card>

                    {lobby.status === 'open' && clubId === lobby.creatorClubId && (
                        <Card className="ring-primary/20">
                            <CardHeader>
                                <h2 className="text-lg font-bold">Iniciar competencia</h2>
                                <CardDescription>Al iniciar se cierran las inscripciones y se programan los partidos.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <p className="text-sm text-muted-foreground">Clubes inscriptos: {lobby.registeredTeams}. Mínimo para iniciar: {lobby.minTeams}.</p>
                                    <Button type="button" onClick={handleStartLeague} disabled={starting || loading || lobby.registeredTeams < lobby.minTeams}>
                                        <Play aria-hidden="true"/>{starting ? 'Iniciando…' : 'Iniciar liga'}
                                    </Button>
                                </div>
                                {startError && <Alert variant="destructive"><CircleAlert aria-hidden="true"/><AlertDescription>{startError}</AlertDescription></Alert>}
                            </CardContent>
                        </Card>
                    )}

                    {started && (
                        <LeagueFixture key={id} id={id} clubId={clubId} clubs={lobby.clubs}
                            leagueStatus={lobby.status} isRegistered={lobby.isRegistered}
                            refresh={refresh} onRefresh={() => setRefresh(value => value + 1)}/>
                    )}

                    <Card>
                        <CardHeader>
                            <h2 className="text-lg font-bold">Clubes inscriptos ({lobby.registeredTeams}/{lobby.maxTeams})</h2>
                            <CardDescription>{lobby.isRegistered ? 'Tu club está inscripto.' : 'Tu club no está inscripto.'}</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {lobby.clubs.length === 0 ? (
                                <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Todavía no hay clubes inscriptos.</p>
                            ) : (
                                <ul className="list-none divide-y rounded-lg border px-4">
                                    {lobby.clubs.map(club => (
                                        <li key={club.id} className="flex items-center justify-between gap-3 py-3">
                                            <Link to={routePath(routes.clubProfile, {clubId: club.id})} className="min-w-0 font-medium wrap-anywhere hover:underline focus-visible:rounded focus-visible:outline-ring">
                                                {club.name}
                                            </Link>
                                            {club.id === lobby.creatorClub?.id && <Badge variant="secondary">Creador</Badge>}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </CardContent>
                    </Card>

                    {lobby.status === 'open' && lobby.isRegistered && (
                        <div className="flex justify-end">
                            <Button type="button" size="sm" variant="destructive" onClick={handleLeaveLeague} disabled={loading || starting}>
                                {clubId === lobby.creatorClubId ? 'Cancelar' : 'Abandonar'}
                            </Button>
                        </div>
                    )}
                </TabsContent>
                <TabsContent value="ranking">
                    {tab === 'ranking' && <LeagueRanking key={refresh} leagueId={id}/>}
                </TabsContent>
            </Tabs>
        </main>
    );
}

export default LeagueLobby;
