// Client HTTP du module D (Prescription + Donnée clinique), indépendant de client.js (module A).
// URL de l'API : VITE_API_URL (défaut « /api », redirigé vers le back-end par le proxy Vite).
import { ApiError } from './client.js';

const BASE = import.meta.env.VITE_API_URL || '/api';

function formatDetail(detail) {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => `${(d.loc || []).slice(1).join('.') || 'champ'} : ${d.msg}`).join(' · ');
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
const enc = encodeURIComponent;

export const apiD = {
  prescriptions: (params) => request('GET', `/prescriptions${qs(params)}`),
  prescription: (id) => request('GET', `/prescriptions/${enc(id)}`),
  prescriptionGraphe: (id) => request('GET', `/prescriptions/${enc(id)}/graphe`),
  createPrescription: (body) => request('POST', '/prescriptions', body),
  updatePrescription: (id, body) => request('PUT', `/prescriptions/${enc(id)}`, body),
  deletePrescription: (id) => request('DELETE', `/prescriptions/${enc(id)}`),
  statistiques: () => request('GET', '/prescriptions/statistiques'),
  alertes: (patient) => request('GET', `/prescriptions/alertes${qs({ patient })}`),

  donnees: (params) => request('GET', `/donnees-cliniques${qs(params)}`),
  donnee: (id) => request('GET', `/donnees-cliniques/${enc(id)}`),
  createDonnee: (body) => request('POST', '/donnees-cliniques', body),
  updateDonnee: (id, body) => request('PUT', `/donnees-cliniques/${enc(id)}`, body),
  deleteDonnee: (id) => request('DELETE', `/donnees-cliniques/${enc(id)}`),

  dossier: (patient) => request('GET', `/module-d/patients/${enc(patient)}/dossier`),
  referentiels: () => request('GET', '/module-d/referentiels'),
  requetes: () => request('GET', '/module-d/requetes'),
  executerRequete: (nom) => request('POST', `/module-d/requetes/${enc(nom)}/executer`),
  sparql: (requete) => request('POST', '/module-d/sparql', { requete }),

  ask: (question) => request('POST', '/module-d/nlp/ask', { question }),
  suggestions: () => request('GET', '/module-d/nlp/suggestions'),
  modele: () => request('GET', '/module-d/nlp/modele'),
};
