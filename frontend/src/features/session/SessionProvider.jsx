import {createContext, useCallback, useContext, useEffect, useRef, useState} from 'react';
import {advanceSessionRevision, request, subscribeToSessionInvalidation} from '@/api/http.js';
import {getMyClub} from '../my-club/api.js';
import {subscribeToClubUpdates} from '../my-club/clubEvents.js';

const SessionContext = createContext(null);
export const DISCARD_MESSAGE = 'Tenés cambios sin guardar. ¿Querés descartarlos?';

export function useSession() {
    return useContext(SessionContext);
}

export function SessionProvider({children}) {
    const [session, setSession] = useState({status: 'checking'});
    const pendingCheck = useRef(null);
    const dirtyDrafts = useRef(new Set());

    const registerUnsavedChanges = useCallback((allowNavigation) => {
        const drafts = dirtyDrafts.current;
        drafts.add(allowNavigation);
        return () => drafts.delete(allowNavigation);
    }, []);

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
        if (dirtyDrafts.current.size > 0 && !window.confirm(DISCARD_MESSAGE)) return false;

        await request('/auth/logout', {method: 'POST'});
        for (const allowNavigation of dirtyDrafts.current) allowNavigation();
        clearSession();
        return true;
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
        <SessionContext.Provider value={{...session, refreshSession, clearSession, signOut, registerUnsavedChanges}}>
            {children}
        </SessionContext.Provider>
    );
}
