import {useCallback, useEffect, useRef} from 'react';
import {useBeforeUnload, useBlocker} from 'react-router';
import {DISCARD_MESSAGE, useSession} from '../../session/SessionProvider.jsx';

export {DISCARD_MESSAGE};

export function useUnsavedChanges(isDirty) {
    const allowLeaving = useRef(false);
    const registerUnsavedChanges = useSession()?.registerUnsavedChanges;
    const allowNavigation = useCallback(() => {
        allowLeaving.current = true;
    }, []);

    useEffect(() => {
        if (isDirty) return registerUnsavedChanges?.(allowNavigation);
    }, [isDirty, registerUnsavedChanges, allowNavigation]);

    const blocker = useBlocker(
        () => isDirty && !allowLeaving.current
    );

    useEffect(() => {
        if (blocker.state !== 'blocked') return;

        if (window.confirm(DISCARD_MESSAGE)) {
            blocker.proceed();
        } else {
            blocker.reset();
        }
    }, [blocker]);

    useBeforeUnload(
        useCallback((event) => {
            if (!isDirty || allowLeaving.current) return;

            event.preventDefault();
            event.returnValue = '';
        }, [isDirty])
    );

    return allowNavigation;
}

export function UnsavedChangesGuard({dirty}) {
    useUnsavedChanges(dirty);
    return null;
}
