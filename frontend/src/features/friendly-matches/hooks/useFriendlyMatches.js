import {useEffect, useRef, useState} from 'react';
import {useLocation, useNavigate} from 'react-router';
import {listFriendlyMatches} from '../api.js';

export function useFriendlyMatches() {
    const {pathname, search, hash, state} = useLocation();
    const navigate = useNavigate();
    const params = new URLSearchParams(search);
    const creatorName = params.get('creatorName') ?? '';
    const requestedPage = Number(params.get('page') ?? 1);
    const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
    const [name, setName] = useState(creatorName);
    const [result, setResult] = useState({items: [], total: 0, page: 1, pageSize: 20});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [version, setVersion] = useState(0);
    const timer = useRef(null);
    const request = useRef(null);

    useEffect(() => {
        setName(creatorName);
        clearTimeout(timer.current);
    }, [creatorName, page]);
    useEffect(() => () => clearTimeout(timer.current), []);

    useEffect(() => {
        const controller = new AbortController();
        request.current = controller;
        setLoading(true);
        setError('');
        listFriendlyMatches({creatorName, page}, controller.signal)
            .then(data => { if (!controller.signal.aborted) setResult(data); })
            .catch(cause => { if (!controller.signal.aborted) setError(cause.message); })
            .finally(() => { if (!controller.signal.aborted) setLoading(false); });
        return () => controller.abort();
    }, [creatorName, page, version]);

    function update(nextName, nextPage) {
        clearTimeout(timer.current);
        request.current?.abort();
        setLoading(true);
        setError('');
        const next = new URLSearchParams(search);
        if (nextName) next.set('creatorName', nextName);
        else next.delete('creatorName');
        if (nextPage === 1) next.delete('page');
        else next.set('page', String(nextPage));
        navigate({pathname, search: next.toString(), hash}, {replace: true, state});
        if (nextName === creatorName && nextPage === page) setVersion(value => value + 1);
    }

    function changeName(value) {
        setName(value);
        clearTimeout(timer.current);
        request.current?.abort();
        setLoading(true);
        setError('');
        timer.current = setTimeout(() => update(value.trim(), 1), 300);
    }

    return {
        name, creatorName, result, loading, error, changeName,
        submit: () => update(name.trim(), 1),
        changePage: nextPage => update(creatorName, nextPage),
        reload: () => update(creatorName, page),
    };
}
