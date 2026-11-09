import {Button} from '@/components/ui/button';
import './FriendlyMatchSearch.css';

export default function FriendlyMatchSearch({search, disabled = false}) {
    const {result, loading} = search;
    return (
        <div className="friendly-match-search">
            <form onSubmit={event => { event.preventDefault(); search.submit(); }}>
                <label htmlFor="friendly-creator-name">Buscar por nombre del club
                    <input id="friendly-creator-name" type="search" value={search.name} disabled={disabled}
                           onChange={event => search.changeName(event.target.value)} placeholder="Nombre del club creador"/>
                </label>
                <Button type="submit" variant="outline" disabled={disabled}>Buscar</Button>
                <Button type="button" variant="outline" disabled={disabled || !search.name}
                        onClick={() => search.changeName('')}>Limpiar</Button>
            </form>
            {result.total > 0 && (
                <nav aria-label="Paginación de amistosos">
                    <Button variant="outline" disabled={disabled || loading || result.page <= 1}
                            onClick={() => search.changePage(result.page - 1)}>Anterior</Button>
                    <span aria-live="polite">Página {result.page} · {result.total} amistosos</span>
                    <Button variant="outline" disabled={disabled || loading || result.page * result.pageSize >= result.total}
                            onClick={() => search.changePage(result.page + 1)}>Siguiente</Button>
                </nav>
            )}
        </div>
    );
}
