const API_URL = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function api(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers['X-Write-Token'] = token;
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Impossible de joindre l’API. Démarrez le backend FastAPI sur le port 8000.', 0);
  }
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' && detail.trim() && !detail.trim().startsWith('<')
      ? detail
      : `L’API a répondu ${response.status}. Vérifiez que le backend FastAPI est démarré sur le port 8000.`;
    throw new ApiError(message, response.status);
  }
  return data;
}

export const SUGGESTIONS = [
  'Quels sont les effets secondaires graves ?',
  'Quels médicaments sont associés à des effets digestifs ?',
  'Quelles sont les contre-indications rénales ?',
  'Quels médicaments sont liés aux allergies ?',
  'Quels effets secondaires sont associés à Doliprane ?',
  'Combien d’effets secondaires sont enregistrés ?',
  'Affiche les contre-indications hépatiques.',
  'L’ibuprofène peut-il provoquer une hémorragie digestive ?',
];
