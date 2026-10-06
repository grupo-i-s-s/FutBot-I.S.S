import {useCallback, useEffect, useRef, useState} from 'react';
import {getMatchSnapshot, matchStreamUrl, validateMatchId} from '../matchApi.js';
import {isTerminal, validateSnapshot} from '../matchSnapshot.js';

const RETRY_DELAYS = [500, 1000, 2000, 4000, 8000];
const emptyView = {snapshot: null, connectionStatus: 'loading', error: ''};

export function useMatchConnection(matchId) {
    const [view, setView] = useState(emptyView);
    const [retryVersion, setRetryVersion] = useState(0);
    const lastSnapshot = useRef(null);
    const retry = useCallback(() => setRetryVersion((version) => version + 1), []);

    useEffect(() => {
        let id;
        try {
            id = validateMatchId(matchId);
        } catch (cause) {
            lastSnapshot.current = null;
            setView({...emptyView, matchId, connectionStatus: 'error', error: cause.message});
            return;
        }
        let latest = lastSnapshot.current?.matchId === id ? lastSnapshot.current : null;
        let disposed = false;
        let socket = null;
        let retryTimer;
        let silenceTimer;
        let retries = 0;
        const controller = new AbortController();

        function update(connectionStatus, error = '') {
            if (!disposed) setView({matchId, snapshot: latest, connectionStatus, error});
        }

        function closeSocket() {
            clearTimeout(silenceTimer);
            if (!socket) return;
            socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null;
            socket.close(1000);
            socket = null;
        }

        function fail(cause) {
            clearTimeout(retryTimer);
            closeSocket();
            update('error', cause.message);
        }

        function accept(data) {
            const snapshot = validateSnapshot(data, id);
            if (latest && snapshot.sequence <= latest.sequence) return false;
            latest = snapshot;
            lastSnapshot.current = snapshot;
            return true;
        }

        function scheduleReconnect() {
            if (disposed || isTerminal(latest)) return;
            closeSocket();
            if (retries >= RETRY_DELAYS.length) {
                update('disconnected', 'No pudimos recuperar la conexión. Podés reintentar.');
                return;
            }
            update('reconnecting', 'Conexión interrumpida. El marcador muestra el último estado recibido.');
            retryTimer = setTimeout(connect, RETRY_DELAYS[retries++]);
        }

        function watchSilence(milliseconds) {
            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(scheduleReconnect, milliseconds);
        }

        async function connect() {
            if (disposed) return;
            update(latest ? 'reconnecting' : 'loading');
            try {
                // HTTP permite distinguir sesión vencida, falta de permiso e inexistencia,
                // errores que el handshake WebSocket no expone al JavaScript del cliente.
                const snapshot = await getMatchSnapshot(id, controller.signal);
                if (disposed) return;
                accept(snapshot);
                if (isTerminal(latest)) {
                    update('finished');
                    return;
                }
                update('connecting');
                socket = new WebSocket(matchStreamUrl(id));
                watchSilence(10_000);
                socket.onopen = () => {
                    if (!disposed) watchSilence(10_000);
                };
                socket.onmessage = (event) => {
                    if (disposed) return;
                    try {
                        const advanced = accept(JSON.parse(event.data));
                        update(isTerminal(latest) ? 'finished' : 'connected');
                        if (isTerminal(latest)) {
                            closeSocket();
                            return;
                        }
                        // WAITING puede estar quieto indefinidamente. RUNNING debe recibir
                        // nuevos estados; una conexión abierta no demuestra que el motor avance.
                        if (advanced || latest.state.status === 'WAITING') retries = 0;
                        clearTimeout(silenceTimer);
                        if (latest.state.status === 'RUNNING') watchSilence(5000);
                    } catch (cause) {
                        fail(cause instanceof SyntaxError ? new Error('El servidor envió un mensaje de partido incompatible.') : cause);
                    }
                };
                socket.onerror = () => { /* onclose recupera el estado por HTTP. */
                };
                socket.onclose = (event) => {
                    if (disposed || isTerminal(latest)) return;
                    if (event.code === 1008) {
                        fail(new Error(event.reason || 'La sesión venció o ya no tenés acceso al partido.'));
                    } else {
                        scheduleReconnect();
                    }
                };
            } catch (cause) {
                if (disposed || cause.name === 'AbortError') return;
                if (cause.status === 0 || cause.status >= 500) scheduleReconnect();
                else fail(cause);
            }
        }

        update(latest ? 'reconnecting' : 'loading');
        void connect();
        return () => {
            disposed = true;
            controller.abort();
            clearTimeout(retryTimer);
            closeSocket();
        };
    }, [matchId, retryVersion]);

    // No mostrar durante un frame el partido anterior al cambiar el parámetro.
    return {...(view.matchId === matchId ? view : emptyView), retry};
}
