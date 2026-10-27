import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi, useDebounced } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, CLASS_LABELS, fmtPrix, exportCsv } from '../app/ui.jsx';
import { MedicamentForm } from '../app/forms.jsx';
import { useToast } from '../app/Toast.jsx';

export default function Medicaments() {
  const [q, setQ] = useState('');
  const [type, setType] = useState('');
  const [ordonnance, setOrdonnance] = useState('');
  const [forme, setForme] = useState('');
  const [prixMax, setPrixMax] = useState(20);
  const [tri, setTri] = useState('label');
  const [creating, setCreating] = useState(false);
  const dq = useDebounced(q);
  const dPrix = useDebounced(prixMax, 250);
  const navigate = useNavigate();
  const notify = useToast();

  const list = useApi(
    () => api.medicaments({ q: dq, type, ordonnance, forme, prixMax: dPrix < 20 ? dPrix : undefined, tri }),
    [dq, type, ordonnance, forme, dPrix, tri],
  );
  const ref = useApi(() => api.referentiels(), []);
  const rows = list.data || [];

  return (
    <>
      <PageHeader
        eyebrow="Module A · Classe Medicament"
        title="Médicaments"
        actions={<button type="button" className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} aria-hidden="true" /> Nouveau médicament</button>}
      >
        <p>Chaque filtre ajoute une contrainte à la requête SPARQL (FILTER, motif de triplet ou chemin de classe).</p>
      </PageHeader>

      <div className="filter-bar">
        <label className="search">
          <Search size={16} aria-hidden="true" />
          <input type="search" placeholder="Nom ou molécule…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher un médicament" />
        </label>
        <select className="input input-sm" value={type} onChange={(e) => setType(e.target.value)} aria-label="Type">
          <option value="">Tous les types</option>
          <option value="Princeps">Princeps</option>
          <option value="Generique">Générique</option>
        </select>
        <select className="input input-sm" value={ordonnance} onChange={(e) => setOrdonnance(e.target.value)} aria-label="Délivrance">
          <option value="">Avec ou sans ordonnance</option>
          <option value="false">Sans ordonnance</option>
          <option value="true">Sur ordonnance</option>
        </select>
        <select className="input input-sm" value={forme} onChange={(e) => setForme(e.target.value)} aria-label="Forme galénique">
          <option value="">Toutes les formes</option>
          {(ref.data?.formes || []).map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
        <label className="range">
          <span>Prix max : <strong>{prixMax < 20 ? fmtPrix(prixMax) : 'illimité'}</strong></span>
          <input type="range" min="1" max="20" step="0.5" value={prixMax} onChange={(e) => setPrixMax(Number(e.target.value))} aria-label="Prix maximum" />
        </label>
        <select className="input input-sm" value={tri} onChange={(e) => setTri(e.target.value)} aria-label="Trier">
          <option value="label">Tri : nom</option>
          <option value="prix">Tri : prix ↑</option>
          <option value="prix_desc">Tri : prix ↓</option>
        </select>
        <button type="button" className="btn btn-compact" disabled={!rows.length} onClick={() => exportCsv('medicaments.csv', ['id', 'label', 'type', 'classe', 'formeGalenique', 'surOrdonnance', 'prixDT'], rows)}>Exporter CSV</button>
      </div>

      <ErrorBox message={list.error} onRetry={list.reload} />
      {list.loading && !list.data ? <Loading /> : rows.length === 0 ? <Empty>Aucun médicament ne correspond à ces filtres.</Empty> : (
        <ul className="med-grid">
          {rows.map((m) => (
            <li key={m.id}>
              <Link to={`/medicaments/${m.id}`} className="med-card">
                <div className="med-card-top">
                  <Badge tone={m.type === 'Generique' ? 'gold' : 'dark'}>{CLASS_LABELS[m.type] || m.type}</Badge>
                  <Badge tone={m.surOrdonnance ? 'danger' : 'neutral'}>{m.surOrdonnance ? 'Sur ordonnance' : 'Sans ordonnance'}</Badge>
                </div>
                <h3>{m.label}</h3>
                <p className="muted small">{m.formeGalenique} · {m.molecules.map((x) => x.label).join(' + ')}</p>
                <p className="med-price">{fmtPrix(m.prixDT)}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <SparqlPanel items={list.sparql} />

      {creating && (
        <MedicamentForm
          onClose={() => setCreating(false)}
          onSaved={(res) => {
            notify(`Médicament « ${res.data.label} » créé (INSERT DATA)`);
            navigate(`/medicaments/${res.data.id}`);
          }}
        />
      )}
    </>
  );
}
