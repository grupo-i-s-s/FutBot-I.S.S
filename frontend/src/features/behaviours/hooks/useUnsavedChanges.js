import {useCallback, useEffect, useRef} from 'react';
import {useBeforeUnload, useBlocker} from 'react-router';

export const DISCARD_MESSAGE =
    'Tenés cambios sin guardar. ¿Querés descartarlos?';

export function useUnsavedChanges(isDirty) {
    const allowLeaving = useRef(false);

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

    return () => {
        allowLeaving.current = true;
    };
}

export function UnsavedChangesGuard({dirty}) {
    useUnsavedChanges(dirty);
    return null;
}