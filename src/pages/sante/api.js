// Client API des pages Pathologie + Personne : tous leurs appels au backend commun passent par ici.
// (Les pages du module A utilisent src/api/client.js, dont les réponses ont la forme { data, sparql }.)
const BASE = import.meta.env.VITE_API_URL || '/api';

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Erreurs de ce module : { code, message, details } ; erreurs de validation FastAPI : { detail: [...] }
function toError(status, data) {
  if (typeof data !== 'object' || data === null) return new ApiError(status, 'error', data || `Erreur ${status}`);
  if (data.message) return new ApiError(status, data.code || 'error', data.message, data.details);
  if (Array.isArray(data.detail)) {
    const details = data.detail.map((d) => ({ champ: (d.loc || []).slice(1).join('.'), message: d.msg }));
    return new ApiError(status, 'validation_error', 'Données invalides', details);
  }
  return new ApiError(status, 'error', data.detail || `Erreur ${status}`);
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
    throw new ApiError(0, 'offline', 'Serveur injoignable. Le back-end est-il lancé (port 8000) ?');
  }
  if (res.status === 204) return null;
  const isJson = (res.headers.get('content-type') || '').includes('json');
  const data = isJson && !raw ? await res.json() : await res.text();
  if (!res.ok) throw toError(res.status, data);
  return data;
}

const enc = encodeURIComponent;

export const api = {
  stats: (o) => request('GET', '/sante/stats', o),
  list: (resource, params, o) => request('GET', `/${resource}`, { ...o, params }),
  get: (resource, id, o) => request('GET', `/${resource}/${enc(id)}`, o),
  create: (resource, body) => request('POST', `/${resource}`, { body }),
  update: (resource, id, body) => request('PATCH', `/${resource}/${enc(id)}`, { body }),
  remove: (resource, id) => request('DELETE', `/${resource}/${enc(id)}`),
  addPathology: (pid, patho) => request('POST', `/patients/${enc(pid)}/pathologies/${enc(patho)}`),
  removePathology: (pid, patho) => request('DELETE', `/patients/${enc(pid)}/pathologies/${enc(patho)}`),
  patientRdf: (pid) => request('GET', `/patients/${enc(pid)}/rdf`, { raw: true }),
  alertes: (params, o) => request('GET', '/alertes', { ...o, params }),
  search: (q, o) => request('GET', '/sante/recherche', { ...o, params: { q } }),
  graph: (id, o) => request('GET', `/sante/graphe/${enc(id)}`, o),
  ask: (question, o) => request('POST', '/sante/nlp/ask', { ...o, body: { question } }),
  exemples: (o) => request('GET', '/sante/nlp/exemples', o),
};
