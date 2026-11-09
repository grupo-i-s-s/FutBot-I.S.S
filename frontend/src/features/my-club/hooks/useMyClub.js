import { useCallback, useEffect, useState } from 'react';
import { getMyClub, listBehaviours, listMyLeagues, listPlayers } from '../api';

function withBehaviourName(players, behaviours) {
    const behaviourNames = new Map(behaviours.map((behaviour) => [behaviour.id, behaviour.name]));

    return players.map((player) => ({
        ...player,
        behaviourName:
            player.behaviour?.name ?? behaviourNames.get(player.behaviorId) ?? 'Sin comportamiento',
    }));
}

export function useMyClub(page = 1, pageSize = 9) {
    const [status, setStatus] = useState('loading');
    const [error, setError] = useState(null);
    const [club, setClub] = useState(null);
    const [roster, setRoster] = useState({items: [], totalPages: 1, total: null});
    const [rosterAttempt, setRosterAttempt] = useState(0);
    const [behaviours, setBehaviours] = useState([]);
    const [attempt, setAttempt] = useState(0);
    const [leagues, setLeagues] = useState([]);

    useEffect(() => {
        const controller = new AbortController();
        const options = { signal: controller.signal };

        async function loadClub() {
            setStatus('loading');
            setError(null);
            try {
                const [clubData, behaviourData, leagueData] = await Promise.all([
                    getMyClub(options),
                    listBehaviours(options),
                    listMyLeagues(options),
                ]);
                if (controller.signal.aborted) return;
                setClub(clubData);
                setBehaviours(behaviourData.items);
                setLeagues(leagueData.items);
                setStatus('ready');
            } catch (loadError) {
                // Una petición cancelada al desmontar no es un error para mostrar.
                if (controller.signal.aborted || loadError.name === 'AbortError') return;
                setError(loadError);
                setStatus('error');
            }
        }

        loadClub();
        return () => controller.abort();
    }, [attempt]);

    useEffect(() => {
        const controller = new AbortController();
        const query = {page, pageSize, attempt: rosterAttempt};

        async function loadRoster() {
            try {
                const {items, totalPages, total} = await listPlayers({page, pageSize, signal: controller.signal});
                if (!controller.signal.aborted) setRoster({items, totalPages, total, query, error: null});
            } catch (loadError) {
                if (!controller.signal.aborted && loadError.name !== 'AbortError') {
                    setRoster(current => ({...current, query, error: loadError}));
                }
            }
        }

        loadRoster();
        return () => controller.abort();
    }, [page, pageSize, rosterAttempt]);

    const reload = useCallback(() => setAttempt((value) => value + 1), []);
    const reloadRoster = useCallback(() => setRosterAttempt(value => value + 1), []);
    const rosterLoading = !roster.query || roster.query.page !== page
        || roster.query.pageSize !== pageSize || roster.query.attempt !== rosterAttempt;

    return {
        status, error, club, behaviours, leagues, reload, setClub,
        players: withBehaviourName(roster.items, behaviours),
        totalPages: roster.totalPages, totalPlayers: roster.total,
        rosterLoading, rosterError: rosterLoading ? null : roster.error, reloadRoster,
    };
}
