import { useCallback, useEffect, useState } from 'react';

// Charge des données ; annule la requête précédente si les dépendances changent ou si le composant disparaît.
export function useApi(fetcher, deps) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher(ctrl.signal)
      .then((data) => setState({ loading: false, error: null, data }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ loading: false, error, data: null });
      });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

export function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

// localStorage protégé (navigation privée, stockage bloqué…)
export const storage = {
  get(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* stockage indisponible : on ignore */
    }
  },
};

export function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = Object.assign(document.createElement('a'), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}

export function toCsv(vars, rows) {
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  return [vars.map(esc).join(';'), ...rows.map((r) => vars.map((v) => esc(r[v])).join(';'))].join('\n');
}
