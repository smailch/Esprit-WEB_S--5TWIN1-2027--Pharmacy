import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Pencil, Trash2, Scale, ArrowRight } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, InferredBadge, CLASS_LABELS, fmtPrix } from '../app/ui.jsx';
import { MedicamentForm } from '../app/forms.jsx';
import ResultGraph from '../app/ResultGraph.jsx';
import { useToast } from '../app/Toast.jsx';

export default function MedicamentDetail() {
  const { id } = useParams();
  const res = useApi(() => api.medicament(id), [id]);
  const alt = useApi(() => api.alternatives(id), [id]);
  const graph = useApi(() => api.graphe(id), [id]);
  const [editing, setEditing] = useState(false);
  const navigate = useNavigate();
  const notify = useToast();
  const m = res.data;

  const remove = async () => {
    if (!window.confirm(`Supprimer définitivement ${m.label} ?`)) return;
    try {
      await api.deleteMedicament(id);
      notify(`${m.label} supprimé (DELETE WHERE)`);
      navigate('/medicaments');
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  if (res.loading && !m) return <Loading />;
  if (res.error) return <><Link to="/medicaments" className="back"><ArrowLeft size={16} /> Médicaments</Link><ErrorBox message={res.error} /></>;

  const best = alt.data?.meilleure;
  return (
    <>
      <Link to="/medicaments" className="back"><ArrowLeft size={16} aria-hidden="true" /> Médicaments</Link>
      <PageHeader
        eyebrow={`Médicament · :${m.id}`}
        title={m.label}
        actions={<>
          <button type="button" className="btn btn-ghost" onClick={() => setEditing(true)}><Pencil size={16} aria-hidden="true" /> Modifier</button>
          <button type="button" className="btn btn-danger" onClick={remove}><Trash2 size={16} aria-hidden="true" /> Supprimer</button>
        </>}
      >
        <ul className="badge-list">
          {m.classes.map((c) => <li key={c.id}><Badge tone={c.inferee ? 'neutral' : 'dark'}>{CLASS_LABELS[c.id] || c.label}</Badge>{c.inferee && <InferredBadge />}</li>)}
        </ul>
      </PageHeader>

      <div className="kpis">
        <div className="kpi"><span className="kpi-label">Prix</span><span className="kpi-value">{fmtPrix(m.prixDT)}</span></div>
        <div className="kpi"><span className="kpi-label">Dosage</span><span className="kpi-value">{m.dosage || '—'}</span></div>
        <div className="kpi"><span className="kpi-label">Forme</span><span className="kpi-value">{m.formeGalenique || '—'}</span></div>
        <div className="kpi"><span className="kpi-label">Ordonnance (ASK)</span><span className="kpi-value">{m.surOrdonnance ? 'Oui' : 'Non'}</span></div>
      </div>

      {best && (
        <Link to={`/comparateur?medicament=${m.id}`} className="callout">
          <Scale size={20} aria-hidden="true" />
          <span><strong>{best.label}</strong> a la même composition pour {fmtPrix(best.economie)} de moins (−{best.economiePct} %).</span>
          <ArrowRight size={18} aria-hidden="true" />
        </Link>
      )}

      <div className="cards-2">
        <section className="panel">
          <h2 className="panel-title">Molécules (contientMolecule)</h2>
          <ul className="link-list">
            {m.molecules.map((x) => <li key={x.id}><Link to={`/molecules/${x.id}`}>{x.label}</Link><span className="mono small">{x.atc}</span></li>)}
          </ul>
        </section>

        <section className="panel">
          <h2 className="panel-title">Indiqué pour (estIndiquePour)</h2>
          {m.indications.length ? (
            <ul className="link-list">{m.indications.map((p) => <li key={p.id}><span>{p.label}</span><span className="mono small">{p.cim10}</span></li>)}</ul>
          ) : <Empty>Aucune indication renseignée.</Empty>}
        </section>

        <section className="panel">
          <h2 className="panel-title">Contre-indiqué pour <InferredBadge /></h2>
          <p className="muted small">Propriété <code>estContreIndiquePour</code> déduite par la chaîne OWL : contientMolecule ∘ aContreIndication ∘ concernePathologie.</p>
          {m.contreIndications.length || m.contreIndicationsGenerales.length ? (
            <ul className="link-list">
              {m.contreIndications.map((c) => (
                <li key={c.id + c.ci}>
                  <span><strong>{c.label}</strong><span className="muted small"> via {c.viaLabel} → {c.ciLabel}</span></span>
                  <Badge tone={c.risque === 'absolu' ? 'danger' : 'gold'}>{c.risque}</Badge>
                </li>
              ))}
              {m.contreIndicationsGenerales.map((c) => (
                <li key={c.ci}><span><strong>{c.ciLabel}</strong><span className="muted small"> via {c.viaLabel}</span></span><Badge tone={c.risque === 'absolu' ? 'danger' : 'gold'}>{c.risque}</Badge></li>
              ))}
            </ul>
          ) : <Empty>Aucune contre-indication.</Empty>}
        </section>

        <section className="panel">
          <h2 className="panel-title">Effets secondaires possibles</h2>
          {m.effets.length ? (
            <ul className="link-list">
              {m.effets.map((e) => <li key={e.effet + e.molecule}><span>{e.label}<span className="muted small"> ({e.molecule})</span></span><Badge tone={e.gravite === 'grave' ? 'danger' : 'neutral'}>{e.gravite}</Badge></li>)}
            </ul>
          ) : <Empty>Aucun effet renseigné.</Empty>}
        </section>
      </div>

      <section className="panel">
        <h2 className="panel-title">Graphe de connaissances (requête CONSTRUCT)</h2>
        {graph.loading && !graph.data ? <Loading /> : <ResultGraph data={graph.data} />}
      </section>

      <SparqlPanel items={[...res.sparql, ...alt.sparql, ...graph.sparql]} />

      {editing && (
        <MedicamentForm
          initial={m}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            notify('Médicament modifié (DELETE / INSERT WHERE)');
            res.reload(); alt.reload(); graph.reload();
          }}
        />
      )}
    </>
  );
}
