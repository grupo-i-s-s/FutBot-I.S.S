import { useEffect, useState } from 'react';
import { getLeagues } from './api';
import { Link } from 'react-router';
import {ArrowLeft, ArrowRight, CircleAlert, Globe, LockKeyhole, Plus, Search, Trophy, Users} from 'lucide-react';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardContent} from '@/components/ui/card';
import {Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle} from '@/components/ui/empty';
import {Field, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {routePath, routes} from '@/routes.js';

export default function LeagueListPage() {
    const [name, setName] = useState('');
    const [search, setSearch] = useState({ name: '' });
    const [leagues, setLeagues] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const controller = new AbortController();

        async function loadLeagues() {
            setIsLoading(true);
            setError(null);

            try {
                const response = await getLeagues(
                    search.name,
                    controller.signal
                );

                if (!controller.signal.aborted) {
                    setLeagues(response.items);
                }
            } catch (error) {
                if (!controller.signal.aborted) {
                    setError(error);
                }
            } finally {
                if (!controller.signal.aborted) {
                    setIsLoading(false);
                }
            }
        }

        loadLeagues();

        return () => controller.abort();
    }, [search]);

    function handleSubmit(event) {
        event.preventDefault();
        setIsLoading(true);
        setError(null);
        setSearch({ name: name.trim() });
    }

    function handleRetry() {
        setIsLoading(true);
        setError(null);
        setSearch({ name: search.name });
    }

    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
            <Link to={routes.myClub} className={buttonVariants({variant: 'outline'})}>
                <ArrowLeft aria-hidden="true"/> Volver a mi club
            </Link>

            <header className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
                        <Trophy className="size-6" aria-hidden="true"/>
                    </span>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Ligas disponibles</h1>
                        <p className="mt-1 text-sm text-muted-foreground">Encontrá una competencia para tu club.</p>
                    </div>
                </div>
                <div className="flex flex-wrap gap-2">
                    <Link to={routes.createLeague} className={buttonVariants()}>
                        <Plus aria-hidden="true"/> Crear liga pública
                    </Link>
                    <Link to={routes.createPrivateLeague} className={buttonVariants({variant: 'outline'})}>
                        <LockKeyhole aria-hidden="true"/> Crear liga privada
                    </Link>
                </div>
            </header>

            <Card>
                <CardContent>
                    <form onSubmit={handleSubmit} className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-end">
                        <Field className="flex-1">
                            <FieldLabel htmlFor="league-name">Buscar por nombre</FieldLabel>
                            <Input id="league-name" type="search" placeholder="Nombre de la liga" className="h-10"
                                value={name} onChange={(event) => setName(event.target.value)}/>
                        </Field>
                        <Button type="submit" className="h-10"><Search aria-hidden="true"/> Buscar</Button>
                    </form>
                </CardContent>
            </Card>

            <section aria-label="Resultados de ligas" aria-busy={isLoading}>
                {isLoading && <Card><CardContent><p role="status" className="py-6 text-center text-sm text-muted-foreground">Cargando ligas...</p></CardContent></Card>}

                {!isLoading && error && (
                    <Alert variant="destructive">
                        <CircleAlert aria-hidden="true"/>
                        <AlertDescription className="space-y-3">
                            <p>{error.status === 401 ? 'Iniciá sesión para consultar las ligas.' : error.message || 'No se pudieron cargar las ligas.'}</p>
                            {error.status === 401 ? (
                                <Link to={routes.signIn} className={buttonVariants({variant: 'outline'})}>Iniciar sesión</Link>
                            ) : <Button type="button" variant="outline" onClick={handleRetry}>Reintentar</Button>}
                        </AlertDescription>
                    </Alert>
                )}

                {!isLoading && !error && leagues.length === 0 && (
                    <Empty className="border bg-card py-12" role="status">
                        <EmptyHeader>
                            <EmptyMedia variant="icon"><Trophy aria-hidden="true"/></EmptyMedia>
                            <EmptyTitle>{search.name ? 'Sin resultados' : 'No hay ligas disponibles.'}</EmptyTitle>
                            <EmptyDescription>{search.name ? `No se encontraron ligas con el nombre "${search.name}".` : 'Podés crear una liga e invitar a otros clubes.'}</EmptyDescription>
                        </EmptyHeader>
                    </Empty>
                )}

                {!isLoading && !error && leagues.length > 0 && (
                    <ul className="grid list-none gap-3 p-0">
                        {leagues.map((league) => (
                            <li key={league.id} className="min-w-0">
                                <Card className="gap-0 rounded-2xl py-0 transition-shadow hover:shadow-md">
                                    <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
                                        <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary" aria-hidden="true">
                                            <Trophy className="size-6"/>
                                        </span>
                                        <div className="min-w-0 flex-1 space-y-2">
                                            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                                                <h2 className="text-lg font-bold tracking-tight wrap-anywhere">{league.name}</h2>
                                                <Badge variant="outline" className={league.status === 'open' ? 'border-primary/15 bg-secondary text-primary' : ''}>
                                                    {{open: 'En espera', running: 'En curso', finished: 'Finalizada', cancelled: 'Cancelada'}[league.status] ?? league.status}
                                                </Badge>
                                            </div>
                                            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
                                                <span className="inline-flex items-center gap-1.5">
                                                    {league.isPrivate ? <LockKeyhole className="size-3.5" aria-hidden="true"/> : <Globe className="size-3.5" aria-hidden="true"/>}
                                                    {league.isPrivate ? 'Privada' : 'Pública'}
                                                </span>
                                                <span className="inline-flex items-center gap-1.5">
                                                    <Users className="size-3.5" aria-hidden="true"/>
                                                    {league.registeredCount}/{league.maxTeams} clubes
                                                </span>
                                                <span>{league.availableSlots} cupos disponibles</span>
                                            </div>
                                            {league.isMember && <p className="text-sm font-medium text-primary">Tu club ya está inscripto.</p>}
                                        </div>
                                        <div className="flex shrink-0 sm:justify-end">
                                            {league.isMember ? (
                                                <Link to={routePath(routes.leagueLobby, {id: league.id})} className={buttonVariants({variant: 'outline', className: 'h-10 w-full sm:w-auto'})}>
                                                    Ver lobby <ArrowRight aria-hidden="true"/>
                                                </Link>
                                            ) : league.canJoin ? (
                                                <Link to={routePath(routes.leagueRegistration, {id: league.id})} className={buttonVariants({className: 'h-10 w-full sm:w-auto'})}>
                                                    Inscribirse <ArrowRight aria-hidden="true"/>
                                                </Link>
                                            ) : <span className="rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">Inscripción no disponible.</span>}
                                        </div>
                                    </CardContent>
                                </Card>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
        </main>
    );
}
