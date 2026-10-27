// Client API unique : tous les appels au backend passent par ici (pas de fetch ailleurs).
// Préfixe propre au module (le backend du module A utilise /api) ; le proxy Vite le redirige vers le port 8001.
const BASE = import.meta.env.VITE_AHMED_API_BASE || '/api-ahmed';

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request(method, path, { body, params, signal, raw } = {}) {
  const url = new URL(BASE + path, window.location.origin);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
  });
  let res;
  try {
    res = await fetch(url, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new ApiError(0, 'offline', 'Le serveur (backend) est injoignable. Lancez-le puis réessayez.');
  }
  if (res.status === 204) return null;
  const isJson = (res.headers.get('content-type') || '').includes('json');
  const data = isJson && !raw ? await res.json() : await res.text();
  if (!res.ok) {
    const err = typeof data === 'object' ? data : { message: data };
    throw new ApiError(res.status, err.code || 'error', err.message || `Erreur ${res.status}`, err.details);
  }
  return data;
}

const enc = encodeURIComponent;

export const api = {
  health: (o) => request('GET', '/health', o),
  reset: () => request('POST', '/admin/reset'),
  stats: (o) => request('GET', '/stats', o),
  list: (resource, params, o) => request('GET', `/${resource}`, { ...o, params }),
  get: (resource, id, o) => request('GET', `/${resource}/${enc(id)}`, o),
  create: (resource, body) => request('POST', `/${resource}`, { body }),
  update: (resource, id, body) => request('PATCH', `/${resource}/${enc(id)}`, { body }),
  remove: (resource, id) => request('DELETE', `/${resource}/${enc(id)}`),
  addPathology: (pid, patho) => request('POST', `/patients/${enc(pid)}/pathologies/${enc(patho)}`),
  removePathology: (pid, patho) => request('DELETE', `/patients/${enc(pid)}/pathologies/${enc(patho)}`),
  patientRdf: (pid) => request('GET', `/patients/${enc(pid)}/rdf`, { raw: true }),
  alertes: (params, o) => request('GET', '/alertes', { ...o, params }),
  search: (q, o) => request('GET', '/search', { ...o, params: { q } }),
  graph: (id, o) => request('GET', `/graph/${enc(id)}`, o),
  ask: (question, o) => request('POST', '/nlp/ask', { ...o, body: { question } }),
  exemples: (o) => request('GET', '/nlp/exemples', o),
  sparql: (query, o) => request('POST', '/sparql', { ...o, body: { query } }),
};
