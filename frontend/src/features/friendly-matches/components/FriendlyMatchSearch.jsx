import {useId} from 'react';
import {Search, X} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious} from '@/components/ui/pagination';

export default function FriendlyMatchSearch({search, disabled = false}) {
    const inputId = useId();

    return (
        <form role="search" aria-label="Buscar amistosos" className="space-y-2"
              onSubmit={event => { event.preventDefault(); search.submit(); }}>
            <Label htmlFor={inputId}>Buscar por nombre del club</Label>
            <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-0 grow basis-52">
                    <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                            aria-hidden="true"/>
                    <Input id={inputId} type="search" className="h-9 bg-background pl-9"
                           value={search.name} disabled={disabled} autoComplete="off"
                           onChange={event => search.changeName(event.target.value)} placeholder="Nombre del club creador"/>
                </div>
                <div className="flex items-center gap-2">
                    <Button type="submit" variant="secondary" size="lg" disabled={disabled}>Buscar</Button>
                    <Button type="button" variant="ghost" size="lg" disabled={disabled || !search.name}
                            onClick={() => search.changeName('')}>
                        <X data-icon="inline-start" aria-hidden="true"/>
                        Limpiar
                    </Button>
                </div>
            </div>
        </form>
    );
}

export function FriendlyMatchPagination({search, disabled = false}) {
    const {result, loading} = search;
    if (result.total === 0) return null;

    return (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
            <span className="text-sm text-muted-foreground" aria-live="polite">
                Página {result.page} · {result.total} {result.total === 1 ? 'amistoso' : 'amistosos'}
            </span>
            <Pagination aria-label="Paginación de amistosos" className="mx-0 w-auto shrink-0">
                <PaginationContent>
                    <PaginationItem>
                        <PaginationPrevious
                            nativeButton type="button" text="Anterior" aria-label="Anterior"
                            disabled={disabled || loading || result.page <= 1}
                            onClick={() => search.changePage(result.page - 1)}
                        />
                    </PaginationItem>
                    <PaginationItem>
                        <PaginationNext
                            nativeButton type="button" text="Siguiente" aria-label="Siguiente"
                            disabled={disabled || loading || result.page * result.pageSize >= result.total}
                            onClick={() => search.changePage(result.page + 1)}
                        />
                    </PaginationItem>
                </PaginationContent>
            </Pagination>
        </div>
    );
}
