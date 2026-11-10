import {useEffect, useRef, useState} from 'react';
import {ArrowLeft, ArrowRight, CircleAlert, Search, Shield, X} from 'lucide-react';
import {Link} from 'react-router';
import {toast} from 'sonner';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardContent, CardHeader} from '@/components/ui/card';
import {Dialog, DialogContent, DialogDescription, DialogTitle} from '@/components/ui/dialog';
import {Empty, EmptyHeader, EmptyMedia, EmptyTitle} from '@/components/ui/empty';
import {Input} from '@/components/ui/input';
import {Item, ItemActions, ItemContent, ItemMedia} from '@/components/ui/item';
import {Label} from '@/components/ui/label';
import {Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious} from '@/components/ui/pagination';
import {Skeleton} from '@/components/ui/skeleton';
import {routes} from '@/routes.js';
import {ClubProfileContent} from '../club-profile/ClubProfilePage';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {getClubs} from './api.js';

const PAGE_SIZE = 20;

export default function ClubsListPage() {
    const [name, setName] = useState('');
    const [search, setSearch] = useState({name: '', page: 1});
    const [result, setResult] = useState({
        items: [],
        page: 1,
        pageSize: PAGE_SIZE,
        total: 0,
        hasNext: false,
    });
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedClub, setSelectedClub] = useState(null);

    const debounceRef = useRef(null);
    const requestRef = useRef(null);
    const loadErrorToastRef = useRef(null);

    useEffect(() => {
        return () => clearTimeout(debounceRef.current);
    }, []);

    useEffect(() => {
        const controller = new AbortController();
        requestRef.current = controller;

        async function loadClubs() {
            setIsLoading(true);
            setError(null);

            try {
                const response = await getClubs(
                    {name: search.name, page: search.page, pageSize: PAGE_SIZE},
                    controller.signal,
                );

                if (!controller.signal.aborted) {
                    setResult(response);
                }
            } catch (requestError) {
                if (!controller.signal.aborted) {
                    setError(requestError);
                    if (search.notifyError && requestError.status !== 401) {
                        loadErrorToastRef.current = toast.error('No se pudieron cargar los clubes', {
                            description: requestError.message,
                        });
                    }
                }
            } finally {
                if (!controller.signal.aborted) {
                    setIsLoading(false);
                }
            }
        }

        loadClubs();

        return () => controller.abort();
    }, [search]);

    function startLoading() {
        requestRef.current?.abort();
        setIsLoading(true);
        setError(null);
    }

    function updateSearch(nextSearch, {notifyError = true} = {}) {
        clearTimeout(debounceRef.current);
        startLoading();
        if (loadErrorToastRef.current !== null) {
            toast.dismiss(loadErrorToastRef.current);
            loadErrorToastRef.current = null;
        }
        setSearch({...nextSearch, notifyError});
    }

    function handleNameChange(event) {
        const nextName = event.target.value;

        setName(nextName);
        clearTimeout(debounceRef.current);
        startLoading();

        debounceRef.current = setTimeout(() => {
            updateSearch({
                name: nextName.trim(),
                page: 1,
            }, {notifyError: false});
        }, 300);
    }

    function handleSubmit(event) {
        event.preventDefault();
        updateSearch({name: name.trim(), page: 1});
    }

    function handleClear() {
        setName('');
        updateSearch({name: '', page: 1});
    }

    function handleRetry() {
        updateSearch(search);
    }

    function handlePageChange(page) {
        updateSearch({...search, page});
    }

    const {items, page, pageSize, total, hasNext} = result;
    const totalPages = Math.ceil(total / pageSize);

    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
            <Card>
                <CardContent className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-4">
                        <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                            <Shield className="size-6" aria-hidden="true"/>
                        </span>
                        <div className="space-y-1">
                            <h1 className="text-2xl font-bold sm:text-3xl">Clubes</h1>
                            <p className="text-muted-foreground">Encontrá otros clubes y consultá sus perfiles.</p>
                        </div>
                    </div>
                    <Link to={routes.myClub} className={buttonVariants({variant: 'outline', size: 'lg'})}>
                        <ArrowLeft data-icon="inline-start" aria-hidden="true"/>
                        Volver a mi club
                    </Link>
                </CardContent>
            </Card>

            <section aria-labelledby="clubs-list-title">
                <Card>
                    <CardHeader className="gap-3 border-b">
                        <h2 id="clubs-list-title" className="text-lg font-bold">Clubes registrados</h2>
                        <form role="search" aria-label="Buscar clubes" className="space-y-2" onSubmit={handleSubmit}>
                            <Label htmlFor="club-name">Buscar por nombre del club</Label>
                            <div className="flex flex-wrap items-center gap-2">
                                <div className="relative min-w-0 grow basis-52">
                                    <Search
                                        className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                                        aria-hidden="true"
                                    />
                                    <Input
                                        id="club-name"
                                        type="search"
                                        className="h-9 bg-background pl-9"
                                        placeholder="Nombre del club"
                                        autoComplete="off"
                                        value={name}
                                        onChange={handleNameChange}
                                    />
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button type="submit" variant="secondary" size="lg">Buscar</Button>
                                    <Button type="button" variant="ghost" size="lg" disabled={!name} onClick={handleClear}>
                                        <X data-icon="inline-start" aria-hidden="true"/>
                                        Limpiar
                                    </Button>
                                </div>
                            </div>
                        </form>
                    </CardHeader>

                    <CardContent className="space-y-4">
                        {isLoading && (
                            <div role="status">
                                <span className="sr-only">Cargando clubes…</span>
                                <div className="grid gap-3 lg:grid-cols-2" aria-hidden="true">
                                    {[1, 2, 3, 4].map(key => <Skeleton key={key} className="h-18 w-full"/>)}
                                </div>
                            </div>
                        )}

                        {!isLoading && error && (
                            <Alert variant="destructive">
                                <CircleAlert aria-hidden="true"/>
                                <AlertTitle>No se pudieron cargar los clubes</AlertTitle>
                                <AlertDescription>
                                    {error.status === 401
                                        ? 'Iniciá sesión para consultar los clubes.'
                                        : error.message || 'Intentá nuevamente.'}
                                </AlertDescription>
                                <div className="col-start-2 pt-2">
                                    {error.status === 401 ? (
                                        <Link to={routes.signIn} className={buttonVariants({variant: 'outline'})}>
                                            Iniciar sesión
                                        </Link>
                                    ) : (
                                        <Button type="button" variant="outline" onClick={handleRetry}>Reintentar</Button>
                                    )}
                                </div>
                            </Alert>
                        )}

                        {!isLoading && !error && (
                            <>
                                {items.length === 0 ? (
                                    <Empty className="border" role="status">
                                        <EmptyHeader>
                                            <EmptyMedia variant="icon"><Shield aria-hidden="true"/></EmptyMedia>
                                            <EmptyTitle>
                                                {total > 0 ? 'No hay clubes en esta página.'
                                                    : search.name ? `No se encontraron clubes con el nombre "${search.name}".`
                                                        : 'No hay clubes registrados.'}
                                            </EmptyTitle>
                                        </EmptyHeader>
                                    </Empty>
                                ) : (
                                    <>
                                        <p className="text-sm text-muted-foreground" aria-live="polite">
                                            Clubes encontrados: {total}
                                        </p>
                                        <ul className="grid gap-3 lg:grid-cols-2" aria-label="Resultados de clubes">
                                            {items.map(club => (
                                                <Item key={club.id} render={<li/>} variant="outline" className="flex-nowrap gap-3">
                                                    <ItemMedia>
                                                        <ClubAvatar avatar={club.avatar} clubName={club.name} size="md"/>
                                                    </ItemMedia>
                                                    <ItemContent className="min-w-0">
                                                        <h3 className="font-semibold wrap-anywhere">{club.name}</h3>
                                                    </ItemContent>
                                                    <ItemActions>
                                                        <Button
                                                            type="button"
                                                            variant="outline"
                                                            onClick={() => setSelectedClub(club)}
                                                            aria-label={`Ver perfil de ${club.name}`}
                                                        >
                                                            Ver perfil
                                                            <ArrowRight data-icon="inline-end" aria-hidden="true"/>
                                                        </Button>
                                                    </ItemActions>
                                                </Item>
                                            ))}
                                        </ul>
                                    </>
                                )}

                                {total > 0 && (
                                    <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
                                        <span className="text-sm text-muted-foreground" aria-live="polite">
                                            Página {page} de {totalPages}
                                        </span>
                                        <Pagination aria-label="Paginación de clubes" className="mx-0 w-auto shrink-0">
                                            <PaginationContent>
                                                <PaginationItem>
                                                    <PaginationPrevious
                                                        nativeButton type="button" text="Anterior" aria-label="Anterior"
                                                        disabled={page <= 1}
                                                        onClick={() => handlePageChange(page - 1)}
                                                    />
                                                </PaginationItem>
                                                <PaginationItem>
                                                    <PaginationNext
                                                        nativeButton type="button" text="Siguiente" aria-label="Siguiente"
                                                        disabled={!hasNext}
                                                        onClick={() => handlePageChange(page + 1)}
                                                    />
                                                </PaginationItem>
                                            </PaginationContent>
                                        </Pagination>
                                    </div>
                                )}
                            </>
                        )}
                    </CardContent>
                </Card>
            </section>
            <Dialog open={Boolean(selectedClub)} onOpenChange={open => { if (!open) setSelectedClub(null); }}>
                <DialogContent className="max-h-[90dvh] overflow-y-auto pt-10 sm:max-w-5xl">
                    <DialogTitle className="sr-only">Perfil de {selectedClub?.name}</DialogTitle>
                    <DialogDescription className="sr-only">Estadísticas y jugadores del club.</DialogDescription>
                    {selectedClub && <ClubProfileContent key={selectedClub.id} clubId={selectedClub.id} embedded/>}
                </DialogContent>
            </Dialog>
        </main>
    );
}
