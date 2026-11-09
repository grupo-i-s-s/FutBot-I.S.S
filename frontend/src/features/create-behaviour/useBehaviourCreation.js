import {useEffect, useRef, useState} from 'react';
import {validateBehaviour} from './api.js';

export function useBehaviourCreation({kind, template, create, onCreated, onRequestStart, onRequestError}) {
    const [name, setName] = useState('');
    const [code, setCode] = useState(template);
    const [error, setError] = useState('');
    const [diagnostics, setDiagnostics] = useState([]);
    const [isValid, setIsValid] = useState(false);
    const [action, setAction] = useState('');
    const pending = useRef(false);

    useEffect(() => () => { pending.current = false; }, []);

    function clearFeedback() {
        setError('');
        setDiagnostics([]);
        setIsValid(false);
    }

    function changeCode(value) {
        setCode(value);
        clearFeedback();
    }

    function reset() {
        setName('');
        changeCode(template);
    }

    async function runRequest(nextAction, request, onSuccess) {
        pending.current = true;
        setAction(nextAction);
        clearFeedback();
        onRequestStart?.();

        try {
            const result = await request();
            if (pending.current) onSuccess(result);
        } catch (requestError) {
            if (!pending.current) return;

            const fallback = nextAction === 'validate'
                ? 'No se pudo validar el comportamiento.'
                : 'No se pudo crear el comportamiento.';
            const message = Object.values(requestError.fields ?? {}).join(' ') || requestError.message || fallback;
            setError(message);
            setDiagnostics(requestError.diagnostics ?? []);
            onRequestError?.(message, nextAction);
        } finally {
            if (pending.current) {
                pending.current = false;
                setAction('');
            }
        }
    }

    function handleValidate() {
        if (pending.current || !code.trim()) return;

        return runRequest('validate', () => validateBehaviour(kind, code), result => {
            setIsValid(result.valid);
            setDiagnostics(result.diagnostics ?? []);
            if (!result.valid) setError('Revisá el código antes de guardarlo.');
        });
    }

    function handleSubmit(event) {
        event.preventDefault();
        if (pending.current) return;

        if (!name.trim() || !code.trim()) {
            clearFeedback();
            setError('Deben completarse todos los campos.');
            return;
        }

        return runRequest('save', () => create(name.trim(), code), onCreated);
    }

    return {
        name, setName, code, changeCode, error, diagnostics, isValid, action, pending,
        dirty: name !== '' || code !== template, reset, handleValidate, handleSubmit,
    };
}
