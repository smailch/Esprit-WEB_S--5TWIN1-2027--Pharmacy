import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, ChevronLeft, ChevronRight, AlertTriangle } from 'lucide-react';
import { apiD } from '../api/moduleD.js';
import { useApi, useDebounced } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, exportCsv } from '../app/ui.jsx';
import { PrescriptionForm } from '../app/formsModuleD.jsx';
import { useToast } from '../app/Toast.jsx';
import '../app/moduleD.css';

export const TYPE_LABELS = {
  PrescriptionSimple: 'Simple', PrescriptionRenouvelable: 'Renouvelable',
  PrescriptionNormale: 'Normale', PrescriptionUrgente: 'Urgente',
  RenouvellementCourt: 'Renouvellement court', RenouvellementLong: 'Renouvellement long',
};

export const fmtDate = (d) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' }) : '—');

export function CategoryBadge({ categorie }) {
  if (!categorie) return null;
  return <Badge tone={categorie === 'PrescriptionRenouvelable' ? 'gold' : 'neutral'}>{TYPE_LABELS[categorie]}</Badge>;
}

const EMPTY_FILTERS = { type: '', patient: '', medecin: '', medicament: '', dateMin: '', dateMax: '' };

export default function Prescriptions() {
  const [q, setQ] = useState('');
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [tri, setTri] = useState('date_desc');
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const dq = useDebounced(q);
  const navigate = useNavigate();
  const notify = useToast();

  useEffect(() => { setPage(1); }, [dq, filters, tri]);

  const list = useApi(() => apiD.prescriptions({ q: dq, ...filters, tri, page, taille: 10 }), [dq, filters, tri, page]);
  const stats = useApi(() => apiD.statistiques(), []);
  const ref = useApi(() => apiD.referentiels(), []);
  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));
  const d = list.data;
  const rows = d?.elements || [];
  const t = stats.data?.totaux;
  const active = Object.values(filters).some(Boolean) || dq;

  return (
    <>
      <PageHeader
        eyebrow="Module D · Classe Prescription"
        title="Prescriptions"
        actions={<button type="button" className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} aria-hidden="true" /> Nouvelle prescription</button>}
      >
        <p>Ordonnances de l’ontologie : un médecin (<code>prescritPar</code>) prescrit un ou plusieurs médicaments (<code>prescritMedicament</code>) à un patient (<code>concernePatient</code>). Chaque filtre ajoute un motif ou un FILTER à la requête SPARQL.</p>
      </PageHeader>

      {t && (
        <div className="kpis">
          <div className="kpi"><span className="kpi-label">Prescriptions</span><span className="kpi-value">{t.prescriptions}</span></div>
          <div className="kpi"><span className="kpi-label">Renouvelables / simples</span><span className="kpi-value">{t.renouvelables} / {t.simples}</span></div>
          <div className="kpi"><span className="kpi-label">Données cliniques</span><span className="kpi-value">{t.donneesCliniques}</span></div>
          <Link to="/scenario" className="kpi kpi-alert"><span className="kpi-label"><AlertTriangle size={13} aria-hidden="true" /> Alertes détectées</span><span className="kpi-value">{t.alertes}</span></Link>
        </div>
      )}

      <div className="filter-bar">
        <label className="search">
          <Search size={16} aria-hidden="true" />
          <input type="search" placeholder="Ordonnance, patient, médecin ou médicament…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher une prescription" />
        </label>
        <select className="input input-sm" value={filters.type} onChange={set('type')} aria-label="Type de prescription">
          <option value="">Tous les types</option>
          <option value="PrescriptionSimple">Simples (toutes)</option>
          <option value="PrescriptionNormale">— Normales</option>
          <option value="PrescriptionUrgente">— Urgentes</option>
          <option value="PrescriptionRenouvelable">Renouvelables (toutes)</option>
          <option value="RenouvellementCourt">— Renouvellement court</option>
          <option value="RenouvellementLong">— Renouvellement long</option>
        </select>
        <select className="input input-sm" value={filters.patient} onChange={set('patient')} aria-label="Patient">
          <option value="">Tous les patients</option>
          {(ref.data?.patients || []).map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
        <select className="input input-sm" value={filters.medecin} onChange={set('medecin')} aria-label="Médecin">
          <option value="">Tous les médecins</option>
          {(ref.data?.medecins || []).map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
        <select className="input input-sm" value={filters.medicament} onChange={set('medicament')} aria-label="Médicament">
          <option value="">Tous les médicaments</option>
          {(ref.data?.medicaments || []).map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
      </div>
      <div className="filter-bar">
        <label className="date-field">Du <input className="input input-sm" type="date" value={filters.dateMin} onChange={set('dateMin')} aria-label="Date de début" /></label>
        <label className="date-field">au <input className="input input-sm" type="date" value={filters.dateMax} onChange={set('dateMax')} aria-label="Date de fin" /></label>
        <select className="input input-sm" value={tri} onChange={(e) => setTri(e.target.value)} aria-label="Trier">
          <option value="date_desc">Tri : plus récentes</option>
          <option value="date">Tri : plus anciennes</option>
          <option value="patient">Tri : patient</option>
          <option value="medecin">Tri : médecin</option>
          <option value="duree">Tri : durée ↓</option>
        </select>
        {active && <button type="button" className="btn-link" onClick={() => { setFilters(EMPTY_FILTERS); setQ(''); }}>Effacer les filtres</button>}
        <button type="button" className="btn btn-compact" disabled={!rows.length} onClick={() => exportCsv('prescriptions.csv', ['id', 'label', 'datePrescription', 'type', 'categorie', 'dureeJours', 'posologie'], rows)}>Exporter CSV</button>
      </div>

      <ErrorBox message={list.error} onRetry={list.reload} />
      {list.loading && !d ? <Loading /> : rows.length === 0 ? <Empty>Aucune prescription ne correspond à ces filtres.</Empty> : (
        <div className="table-scroll panel">
          <table className="data-table is-clickable">
            <thead>
              <tr><th scope="col">Ordonnance</th><th scope="col">Date</th><th scope="col">Type</th><th scope="col">Patient</th><th scope="col">Médecin</th><th scope="col">Médicaments</th><th scope="col">Durée</th></tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id} onClick={() => navigate(`/prescriptions/${p.id}`)}>
                  <th scope="row"><Link to={`/prescriptions/${p.id}`} onClick={(e) => e.stopPropagation()}>{p.id}</Link><span className="muted small block">{p.label}</span></th>
                  <td>{fmtDate(p.datePrescription)}</td>
                  <td><span className="stack">{p.type && <Badge tone="dark">{TYPE_LABELS[p.type]}</Badge>}<CategoryBadge categorie={p.categorie} /></span></td>
                  <td>{p.patient?.label}</td>
                  <td>{p.medecin?.label}</td>
                  <td>{p.medicaments.map((m) => m.label).join(', ')}</td>
                  <td>{p.dureeJours} j</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {d && d.total > 0 && (
        <nav className="pager" aria-label="Pagination">
          <button type="button" className="btn btn-compact" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft size={14} aria-hidden="true" /> Précédent</button>
          <span>Page {d.page} / {d.pages} · {d.total} prescription{d.total > 1 ? 's' : ''}</span>
          <button type="button" className="btn btn-compact" disabled={page >= d.pages} onClick={() => setPage((p) => p + 1)}>Suivant <ChevronRight size={14} aria-hidden="true" /></button>
        </nav>
      )}
      <SparqlPanel items={list.sparql} />

      {creating && (
        <PrescriptionForm
          onClose={() => setCreating(false)}
          onSaved={(res) => {
            notify(`${res.data.label} créée (INSERT DATA)`);
            navigate(`/prescriptions/${res.data.id}`);
          }}
        />
      )}
    </>
  );
}
