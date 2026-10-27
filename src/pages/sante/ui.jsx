import { useEffect, useRef } from 'react';
import { download, toCsv } from './hooks';

export const Loading = ({ label = 'Chargement…' }) => (
  <p className="state" role="status" aria-live="polite"><span className="spinner" aria-hidden="true" />{label}</p>
);

export const Empty = ({ children = 'Aucun résultat.' }) => <p className="state muted">{children}</p>;

export function ErrorBox({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="error-box" role="alert">
      <strong>{error.status === 409 ? 'Action refusée' : error.status === 0 ? 'Backend injoignable' : 'Erreur'}</strong>
      <span>{error.message}</span>
      {Array.isArray(error.details) && error.details.length > 0 && (
        <ul>
          {error.details.map((d, i) => (
            <li key={i}>{d.champ ? `${d.champ} : ${d.message}` : `${d.label || d.id} (${d.relation})`}</li>
          ))}
        </ul>
      )}
      {onRetry && <button className="btn small" onClick={onRetry}>Réessayer</button>}
    </div>
  );
}

// Affiche chargement / erreur / vide / contenu
export function Async({ state, empty, children }) {
  if (state.loading && !state.data) return <Loading />;
  if (state.error) return <ErrorBox error={state.error} onRetry={state.reload} />;
  if (empty && empty(state.data)) return <Empty />;
  return children(state.data);
}

export const Badge = ({ tone = 'neutral', title, children }) => (
  <span className={`badge ${tone}`} title={title}>{children}</span>
);

export function ClasseBadge({ classe, asserte }) {
  return (
    <>
      <Badge tone={classe === 'PatientEnfant' ? 'gold' : 'green'}>{classe === 'PatientEnfant' ? 'Enfant' : 'Adulte'}</Badge>
      {asserte === false && (
        <Badge tone="outline" title="Classe non écrite dans les données : déduite de l'âge (classe définie OWL, raisonneur HermiT)">
          inféré
        </Badge>
      )}
    </>
  );
}

export function Modal({ title, onClose, children }) {
  const ref = useRef(null);
  useEffect(() => {
    const prev = document.activeElement;
    ref.current?.querySelector('input, select, textarea, button')?.focus();
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      prev?.focus?.();
    };
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" ref={ref}>
        <header>
          <h2 id="modal-title">{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Fermer">×</button>
        </header>
        {children}
      </div>
    </div>
  );
}

export const Field = ({ label, hint, children }) => (
  <label className="field">
    <span>{label}</span>
    {children}
    {hint && <small className="muted">{hint}</small>}
  </label>
);

export function Pagination({ total, limit, offset, onChange }) {
  if (total <= limit) return null;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(total / limit);
  return (
    <nav className="pagination" aria-label="Pagination">
      <button className="btn small" disabled={page === 1} onClick={() => onChange(offset - limit)}>Précédent</button>
      <span>Page {page} / {pages} · {total} éléments</span>
      <button className="btn small" disabled={page === pages} onClick={() => onChange(offset + limit)}>Suivant</button>
    </nav>
  );
}

const show = (v) => (typeof v === 'boolean' ? (v ? 'oui' : 'non') : v ?? '—');

// Tableau de résultats générique avec export CSV / JSON
export function ResultTable({ vars, rows, name = 'resultats' }) {
  if (!rows?.length) return <Empty>Aucun résultat dans les données.</Empty>;
  return (
    <div>
      <div className="toolbar end">
        <button className="btn small" onClick={() => download(`${name}.csv`, toCsv(vars, rows), 'text/csv')}>Export CSV</button>
        <button className="btn small" onClick={() => download(`${name}.json`, JSON.stringify(rows, null, 2), 'application/json')}>
          Export JSON
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr>{vars.map((v) => <th key={v} scope="col">{v}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>{vars.map((v) => <td key={v}>{show(r[v])}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AlertBanner({ alertes }) {
  if (!alertes?.length) return null;
  return (
    <div className="alert-banner" role="alert">
      <strong>⚠ {alertes.length} alerte{alertes.length > 1 ? 's' : ''} de sécurité</strong>
      <ul>
        {alertes.map((a, i) => (
          <li key={i}>
            <b>{a.ordonnance}</b> — {a.patient} : <b>{a.medicament}</b> · {a.raison}
            {a.medecin && <span className="muted"> · prescrit par {a.medecin}</span>}
            {a.pharmacien && <span className="muted"> · délivré par {a.pharmacien}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
