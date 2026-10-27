// Client HTTP centralisé vers le back-end. Toutes les réponses ont la forme { data, sparql }.
const BASE = import.meta.env.VITE_API_URL || '/api';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function formatDetail(detail) {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${(d.loc || []).slice(1).join('.') || 'champ'} : ${d.msg}`).join(' · ');
  }
  return JSON.stringify(detail);
}

async function request(method, path, body) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Serveur injoignable. Le back-end est-il lancé (port 8000) ?', 0);
  }
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(formatDetail(json.detail) || `Erreur ${res.status}`, res.status);
  return json;
}

const qs = (params = {}) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, v);
  });
  const s = p.toString();
  return s ? `?${s}` : '';
};

export const api = {
  health: () => request('GET', '/health'),
  reset: () => request('POST', '/admin/reset'),

  molecules: (params) => request('GET', `/molecules${qs(params)}`),
  molecule: (id) => request('GET', `/molecules/${encodeURIComponent(id)}`),
  createMolecule: (body) => request('POST', '/molecules', body),
  updateMolecule: (id, body) => request('PUT', `/molecules/${encodeURIComponent(id)}`, body),
  deleteMolecule: (id) => request('DELETE', `/molecules/${encodeURIComponent(id)}`),

  medicaments: (params) => request('GET', `/medicaments${qs(params)}`),
  medicament: (id) => request('GET', `/medicaments/${encodeURIComponent(id)}`),
  createMedicament: (body) => request('POST', '/medicaments', body),
  updateMedicament: (id, body) => request('PUT', `/medicaments/${encodeURIComponent(id)}`, body),
  deleteMedicament: (id) => request('DELETE', `/medicaments/${encodeURIComponent(id)}`),
  alternatives: (id) => request('GET', `/medicaments/${encodeURIComponent(id)}/alternatives`),
  graphe: (id) => request('GET', `/medicaments/${encodeURIComponent(id)}/graphe`),
  interactions: (medicaments) => request('POST', '/interactions/verifier', { medicaments }),

  hierarchie: () => request('GET', '/hierarchie'),
  stats: () => request('GET', '/stats'),
  referentiels: () => request('GET', '/referentiels'),

  requetes: () => request('GET', '/requetes'),
  executerRequete: (nom) => request('POST', `/requetes/${encodeURIComponent(nom)}/executer`),
  sparql: (requete) => request('POST', '/sparql', { requete }),

  ask: (question) => request('POST', '/nlp/ask', { question }),
  suggestions: () => request('GET', '/nlp/suggestions'),
  modele: () => request('GET', '/nlp/modele'),
};
