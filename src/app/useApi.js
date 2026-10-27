import { useCallback, useEffect, useRef, useState } from 'react';

/** Charge une ressource de l'API ; renvoie { data, sparql, loading, error, reload }. */
export function useApi(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, sparql: [], loading: true, error: null });
  const reqId = useRef(0);

  const load = useCallback(() => {
    const id = ++reqId.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher()
      .then((res) => id === reqId.current && setState({ data: res.data, sparql: res.sparql || [], loading: false, error: null }))
      .catch((err) => id === reqId.current && setState((s) => ({ ...s, loading: false, error: err.message })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { load(); }, [load]);

  return { ...state, reload: load };
}

/** Retarde une valeur (recherche au fil de la frappe). */
export function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}
