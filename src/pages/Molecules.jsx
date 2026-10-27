import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, Search, ChevronRight } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi, useDebounced } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, CLASS_LABELS, exportCsv } from '../app/ui.jsx';
import { MoleculeForm } from '../app/forms.jsx';
import { useToast } from '../app/Toast.jsx';

function Tree({ node, active, onPick, depth = 0 }) {
  return (
    <li>
      <button type="button" className={`tree-node ${active === node.id ? 'is-active' : ''}`} style={{ '--depth': depth }} onClick={() => onPick(node.id)} aria-pressed={active === node.id}>
        <span>{CLASS_LABELS[node.id] || node.label}</span>
        <span className="tree-count">{node.nbIndividus}</span>
      </button>
      {node.enfants.length > 0 && (
        <ul>{node.enfants.map((c) => <Tree key={c.id} node={c} active={active} onPick={onPick} depth={depth + 1} />)}</ul>
      )}
    </li>
  );
}

export default function Molecules() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get('q') || '');
  const classe = params.get('classe') || '';
  const [atc, setAtc] = useState('');
  const [tri, setTri] = useState('label');
  const [creating, setCreating] = useState(false);
  const dq = useDebounced(q);
  const datc = useDebounced(atc);
  const navigate = useNavigate();
  const notify = useToast();

  const list = useApi(() => api.molecules({ q: dq, classe, atc: datc, tri }), [dq, classe, datc, tri]);
  const tree = useApi(() => api.hierarchie(), []);
  const root = tree.data?.find((r) => r.id === 'Molecule');

  const pickClasse = (id) => {
    const next = new URLSearchParams(params);
    if (!id || id === 'Molecule' || id === classe) next.delete('classe');
    else next.set('classe', id);
    setParams(next);
  };

  const rows = list.data || [];
  return (
    <>
      <PageHeader
        eyebrow="Module A · Classe Molecule"
        title="Molécules"
        actions={<button type="button" className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} aria-hidden="true" /> Nouvelle molécule</button>}
      >
        <p>Principes actifs de l’ontologie. Le filtre par classe utilise la hiérarchie : « Antibiotique » inclut les pénicillines et les macrolides.</p>
      </PageHeader>

      <div className="split">
        <aside className="panel tree" aria-label="Hiérarchie des classes">
          <p className="panel-title">Hiérarchie (3 niveaux)</p>
          {tree.loading && <Loading />}
          {root && <ul><Tree node={root} active={classe || 'Molecule'} onPick={pickClasse} /></ul>}
        </aside>

        <section>
          <div className="filter-bar">
            <label className="search">
              <Search size={16} aria-hidden="true" />
              <input type="search" placeholder="Rechercher (avec ou sans accents)…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher une molécule" />
            </label>
            <input className="input input-sm" placeholder="Code ATC (ex. N02)" value={atc} onChange={(e) => setAtc(e.target.value)} aria-label="Filtrer par début de code ATC" />
            <select className="input input-sm" value={tri} onChange={(e) => setTri(e.target.value)} aria-label="Trier">
              <option value="label">Tri : nom</option>
              <option value="atc">Tri : code ATC</option>
              <option value="dose">Tri : dose max ↓</option>
              <option value="medicaments">Tri : nb de médicaments ↓</option>
            </select>
            {classe && <button type="button" className="chip is-active" onClick={() => pickClasse(null)}>{CLASS_LABELS[classe]} ✕</button>}
            <button type="button" className="btn btn-compact" disabled={!rows.length} onClick={() => exportCsv('molecules.csv', ['id', 'label', 'classe', 'codeATC', 'doseMaxJourMg', 'nbMedicaments'], rows)}>Exporter CSV</button>
          </div>

          <ErrorBox message={list.error} onRetry={list.reload} />
          {list.loading && !list.data ? <Loading /> : rows.length === 0 ? <Empty>Aucune molécule ne correspond à ces filtres.</Empty> : (
            <div className="table-scroll panel">
              <table className="data-table is-clickable">
                <thead>
                  <tr><th scope="col">Molécule</th><th scope="col">Classe</th><th scope="col">Code ATC</th><th scope="col">Dose max / j</th><th scope="col">Médicaments</th><th aria-label="Ouvrir" /></tr>
                </thead>
                <tbody>
                  {rows.map((m) => (
                    <tr key={m.id} onClick={() => navigate(`/molecules/${m.id}`)}>
                      <th scope="row"><Link to={`/molecules/${m.id}`} onClick={(e) => e.stopPropagation()}>{m.label}</Link></th>
                      <td><Badge>{CLASS_LABELS[m.classe] || m.classe}</Badge></td>
                      <td className="mono">{m.codeATC || '—'}</td>
                      <td>{m.doseMaxJourMg ? `${m.doseMaxJourMg} mg` : '—'}</td>
                      <td>{m.medicaments.length ? m.medicaments.join(', ') : <span className="muted">aucun</span>}</td>
                      <td><ChevronRight size={16} aria-hidden="true" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <SparqlPanel items={list.sparql} />
        </section>
      </div>

      {creating && (
        <MoleculeForm
          onClose={() => setCreating(false)}
          onSaved={(res) => {
            notify(`Molécule « ${res.data.label} » créée (INSERT DATA)`);
            navigate(`/molecules/${res.data.id}`);
          }}
        />
      )}
    </>
  );
}
