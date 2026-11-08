import {createContext, useCallback, useContext, useEffect, useRef, useState} from 'react';
import {advanceSessionRevision, request, subscribeToSessionInvalidation} from '@/api/http.js';
import {getMyClub} from '../my-club/api.js';
import {subscribeToClubUpdates} from '../my-club/clubEvents.js';

const SessionContext = createContext(null);

export function useSession() {
    return useContext(SessionContext);
}

export function SessionProvider({children}) {
    const [session, setSession] = useState({status: 'checking'});
    const pendingCheck = useRef(null);

    const clearSession = useCallback(() => {
        advanceSessionRevision();
        pendingCheck.current?.abort();
        setSession({status: 'anonymous'});
    }, []);

    const refreshSession = useCallback(async () => {
        advanceSessionRevision();
        pendingCheck.current?.abort();
        const controller = new AbortController();
        pendingCheck.current = controller;
        setSession({status: 'checking'});

        try {
            const club = await getMyClub({signal: controller.signal});
            if (!controller.signal.aborted) setSession({status: 'authenticated', club});
        } catch (error) {
            if (!controller.signal.aborted) {
                setSession(error.status === 401 ? {status: 'anonymous'} : {status: 'error', error});
            }
        }
    }, []);

    async function signOut() {
        await request('/auth/logout', {method: 'POST'});
        clearSession();
    }

    useEffect(() => {
        const unsubscribeSession = subscribeToSessionInvalidation(clearSession);
        const unsubscribeClub = subscribeToClubUpdates((club) => {
            // El guardado confirmado tiene prioridad sobre un GET anterior.
            pendingCheck.current?.abort();
            setSession({status: 'authenticated', club});
        });
        void refreshSession();

        return () => {
            pendingCheck.current?.abort();
            unsubscribeSession();
            unsubscribeClub();
        };
    }, [clearSession, refreshSession]);

    return (
        <SessionContext.Provider value={{...session, refreshSession, clearSession, signOut}}>
            {children}
        </SessionContext.Provider>
    );
}
