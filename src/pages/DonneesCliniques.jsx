import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { apiD } from '../api/moduleD.js';
import { useApi, useDebounced } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, exportCsv } from '../app/ui.jsx';
import { DonneeForm } from '../app/formsModuleD.jsx';
import { useToast } from '../app/Toast.jsx';
import { fmtDate } from './Prescriptions.jsx';
import '../app/moduleD.css';

export const DONNEE_LABELS = {
  SigneVital: 'Signe vital', AnalyseBiologique: 'Analyse biologique', Allergie: 'Allergie', Antecedent: 'Antécédent',
  ExamenClinique: 'Examen clinique', HistoriqueMedical: 'Historique médical',
};

export function valeurDonnee(d) {
  if (d.valeur != null) return `${d.valeur} ${d.unite || ''}`.trim();
  if (d.molecule) return `allergique à ${d.molecule.label}`;
  if (d.pathologie) return d.pathologie.label;
  return '—';
}

const EMPTY = { type: '', patient: '', dateMin: '', dateMax: '' };

export default function DonneesCliniques() {
  const [q, setQ] = useState('');
  const [filters, setFilters] = useState(EMPTY);
  const [tri, setTri] = useState('date_desc');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null); // null | 'new' | donnée
  const dq = useDebounced(q);
  const notify = useToast();

  useEffect(() => { setPage(1); }, [dq, filters, tri]);
  const list = useApi(() => apiD.donnees({ q: dq, ...filters, tri, page, taille: 10 }), [dq, filters, tri, page]);
  const stats = useApi(() => apiD.statistiques(), []);
  const ref = useApi(() => apiD.referentiels(), []);
  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));
  const d = list.data;
  const rows = d?.elements || [];
  const parType = Object.fromEntries((stats.data?.donneesParType || []).map((r) => [r.type, r.nombre]));

  const remove = async (x) => {
    if (!window.confirm(`Supprimer « ${x.label} » de ${x.patient.label} ?`)) return;
    try {
      await apiD.deleteDonnee(x.id);
      notify(`${x.label} supprimée (DELETE WHERE)`);
      list.reload(); stats.reload();
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Module D · Classe DonneeClinique"
        title="Données cliniques"
        actions={<button type="button" className="btn btn-primary" onClick={() => setEditing('new')}><Plus size={16} aria-hidden="true" /> Nouvelle donnée</button>}
      >
        <p>Examens cliniques (<code>SigneVital</code>, <code>AnalyseBiologique</code> : <code>valeur</code>, <code>unite</code>) et historique médical (<code>Allergie</code> → <code>allergiqueA</code>, <code>Antecedent</code> → <code>porteSur</code>), rattachés au patient par <code>estDonneeDe</code>. Ces données alimentent les alertes de prescription.</p>
      </PageHeader>

      <div className="kpis">
        {['SigneVital', 'AnalyseBiologique', 'Allergie', 'Antecedent'].map((t) => (
          <button key={t} type="button" className={`kpi kpi-button ${filters.type === t ? 'is-active' : ''}`} aria-pressed={filters.type === t}
            onClick={() => setFilters((f) => ({ ...f, type: f.type === t ? '' : t }))}>
            <span className="kpi-label">{DONNEE_LABELS[t]}</span><span className="kpi-value">{parType[t] ?? '…'}</span>
          </button>
        ))}
      </div>

      <div className="filter-bar">
        <label className="search">
          <Search size={16} aria-hidden="true" />
          <input type="search" placeholder="Libellé, patient, molécule ou pathologie…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher une donnée clinique" />
        </label>
        <select className="input input-sm" value={filters.type} onChange={set('type')} aria-label="Type de donnée">
          <option value="">Tous les types</option>
          <option value="ExamenClinique">Examens cliniques (tous)</option>
          <option value="SigneVital">— Signes vitaux</option>
          <option value="AnalyseBiologique">— Analyses biologiques</option>
          <option value="HistoriqueMedical">Historique médical (tout)</option>
          <option value="Allergie">— Allergies</option>
          <option value="Antecedent">— Antécédents</option>
        </select>
        <select className="input input-sm" value={filters.patient} onChange={set('patient')} aria-label="Patient">
          <option value="">Tous les patients</option>
          {(ref.data?.patients || []).map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
      </div>
      <div className="filter-bar">
        <label className="date-field">Du <input className="input input-sm" type="date" value={filters.dateMin} onChange={set('dateMin')} aria-label="Date de début" /></label>
        <label className="date-field">au <input className="input input-sm" type="date" value={filters.dateMax} onChange={set('dateMax')} aria-label="Date de fin" /></label>
        <select className="input input-sm" value={tri} onChange={(e) => setTri(e.target.value)} aria-label="Trier">
          <option value="date_desc">Tri : plus récentes</option>
          <option value="date">Tri : plus anciennes</option>
          <option value="patient">Tri : patient</option>
          <option value="type">Tri : type</option>
          <option value="label">Tri : libellé</option>
        </select>
        {(dq || Object.values(filters).some(Boolean)) && <button type="button" className="btn-link" onClick={() => { setFilters(EMPTY); setQ(''); }}>Effacer les filtres</button>}
        <button type="button" className="btn btn-compact" disabled={!rows.length}
          onClick={() => exportCsv('donnees-cliniques.csv', ['id', 'label', 'type', 'dateMesure', 'valeur', 'unite'], rows)}>Exporter CSV</button>
      </div>

      <ErrorBox message={list.error} onRetry={list.reload} />
      {list.loading && !d ? <Loading /> : rows.length === 0 ? <Empty>Aucune donnée clinique ne correspond à ces filtres.</Empty> : (
        <div className="table-scroll panel">
          <table className="data-table">
            <thead><tr><th scope="col">Donnée</th><th scope="col">Type</th><th scope="col">Patient</th><th scope="col">Valeur / détail</th><th scope="col">Date</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.id}>
                  <th scope="row">{x.label}<span className="muted small block mono">:{x.id}</span></th>
                  <td><span className="stack"><Badge tone={x.categorie === 'ExamenClinique' ? 'neutral' : 'gold'}>{DONNEE_LABELS[x.type] || x.type}</Badge></span></td>
                  <td><Link to={`/scenario?patient=${x.patient.id}`}>{x.patient.label}</Link></td>
                  <td>{valeurDonnee(x)}</td>
                  <td>{fmtDate(x.dateMesure)}</td>
                  <td className="row-actions">
                    <button type="button" className="icon-btn" aria-label={`Modifier ${x.label}`} onClick={() => setEditing(x)}><Pencil size={15} /></button>
                    <button type="button" className="icon-btn" aria-label={`Supprimer ${x.label}`} onClick={() => remove(x)}><Trash2 size={15} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {d && d.total > 0 && (
        <nav className="pager" aria-label="Pagination">
          <button type="button" className="btn btn-compact" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft size={14} aria-hidden="true" /> Précédent</button>
          <span>Page {d.page} / {d.pages} · {d.total} donnée{d.total > 1 ? 's' : ''}</span>
          <button type="button" className="btn btn-compact" disabled={page >= d.pages} onClick={() => setPage((p) => p + 1)}>Suivant <ChevronRight size={14} aria-hidden="true" /></button>
        </nav>
      )}
      <SparqlPanel items={list.sparql} />

      {editing && (
        <DonneeForm
          initial={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={(res) => {
            notify(editing === 'new' ? `${res.data.label} créée (INSERT DATA) : :${res.data.id}` : 'Donnée modifiée (DELETE / INSERT WHERE)');
            setEditing(null);
            list.reload(); stats.reload();
          }}
        />
      )}
    </>
  );
}
