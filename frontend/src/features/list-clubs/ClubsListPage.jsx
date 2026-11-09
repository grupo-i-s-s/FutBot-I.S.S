import {useEffect, useRef, useState} from 'react';
import {Link} from 'react-router';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {getClubs} from './api';
import '../login/LoginPage.css';
import './ClubsListPage.css';

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

    const debounceRef = useRef(null);
    const requestRef = useRef(null);

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
                    {...search, pageSize: PAGE_SIZE},
                    controller.signal,
                );

                if (!controller.signal.aborted) {
                    setResult(response);
                }
            } catch (requestError) {
                if (!controller.signal.aborted) {
                    setError(requestError);
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

    function updateSearch(nextSearch) {
        clearTimeout(debounceRef.current);
        startLoading();
        setSearch({...nextSearch});
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
            });
        }, 300);
    }

    function handleSubmit(event) {
        event.preventDefault();
        updateSearch({name: name.trim(), page: 1});
    }

    function handleRetry() {
        updateSearch(search);
    }

    function handlePageChange(page) {
        updateSearch({...search, page});
    }

    const totalPages = Math.ceil(result.total / result.pageSize);

    return (
        <main className="login-page clubs-page">
            <section className="login-card clubs-card">
                <h1 className="login-title">
                    Clubes<br/>FutBot
                </h1>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="club-name">
                            Buscar Club por nombre
                        </label>

                        <input
                            id="club-name"
                            type="search"
                            placeholder="Nombre del club"
                            value={name}
                            onChange={handleNameChange}
                        />
                    </div>

                    <button type="submit" className="login-button">
                        Buscar
                    </button>
                </form>

                <div className="clubs-results" aria-busy={isLoading}>
                    {isLoading && (
                        <p className="clubs-message" role="status">
                            Cargando clubes...
                        </p>
                    )}

                    {!isLoading && error && (
                        <div className="clubs-error" role="alert">
                            <p>
                                {error.status === 401
                                    ? 'Iniciá sesión para consultar los clubes.'
                                    : error.message || 'No se pudieron cargar los clubes.'}
                            </p>

                            {error.status === 401 ? (
                                <Link to="/login" className="clubs-link">
                                    Iniciar sesión
                                </Link>
                            ) : (
                                <button
                                    type="button"
                                    className="login-button"
                                    onClick={handleRetry}
                                >
                                    Reintentar
                                </button>
                            )}
                        </div>
                    )}

                    {!isLoading && !error && (
                        <>
                            {result.items.length === 0 ? (
                                <p className="clubs-message" role="status">
                                    {result.total > 0
                                        ? 'No hay clubes en esta página.'
                                        : search.name
                                            ? `No se encontraron clubes con el nombre "${search.name}".`
                                            : 'No hay clubes registrados.'}
                                </p>
                            ) : (
                                <>
                                    <p className="clubs-summary">
                                        Clubes encontrados: {result.total}
                                    </p>

                                    <ul className="clubs-list">
                                        {result.items.map((club) => (
                                            <li key={club.id} className="club-item">
                                                <ClubAvatar
                                                    avatar={club.avatar}
                                                    clubName={club.name}
                                                    size="md"
                                                />

                                                <div className="club-details">
                                                    <h2 className="club-name">
                                                        {club.name}
                                                    </h2>

                                                    <Link
                                                        to={`/club/${club.id}`}
                                                        className="clubs-link"
                                                        aria-label={`Ver perfil de ${club.name}`}
                                                    >
                                                        Ver perfil
                                                    </Link>
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
                                </>
                            )}

                            {result.total > 0 && (
                                <nav
                                    className="clubs-pagination"
                                    aria-label="Paginación de clubes"
                                >
                                    <button
                                        type="button"
                                        disabled={result.page <= 1}
                                        onClick={() => handlePageChange(result.page - 1)}
                                    >
                                        Anterior
                                    </button>

                                    <span aria-live="polite">
                                        Página {result.page} de {totalPages}
                                    </span>

                                    <button
                                        type="button"
                                        disabled={!result.hasNext}
                                        onClick={() => handlePageChange(result.page + 1)}
                                    >
                                        Siguiente
                                    </button>
                                </nav>
                            )}
                        </>
                    )}
                </div>

                <Link to="/mi-club" className="clubs-link">
                    Volver a mi club
                </Link>
            </section>
        </main>
    );
}