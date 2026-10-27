import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, InferredBadge, CLASS_LABELS, fmtPrix } from '../app/ui.jsx';
import { MoleculeForm } from '../app/forms.jsx';
import { useToast } from '../app/Toast.jsx';

export default function MoleculeDetail() {
  const { id } = useParams();
  const res = useApi(() => api.molecule(id), [id]);
  const [editing, setEditing] = useState(false);
  const navigate = useNavigate();
  const notify = useToast();
  const m = res.data;

  const remove = async () => {
    if (!window.confirm(`Supprimer définitivement ${m.label} ?`)) return;
    try {
      await api.deleteMolecule(id);
      notify(`${m.label} supprimée (DELETE WHERE)`);
      navigate('/molecules');
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  if (res.loading && !m) return <Loading />;
  if (res.error) return <><Link to="/molecules" className="back"><ArrowLeft size={16} /> Molécules</Link><ErrorBox message={res.error} /></>;

  return (
    <>
      <Link to="/molecules" className="back"><ArrowLeft size={16} aria-hidden="true" /> Molécules</Link>
      <PageHeader
        eyebrow={`Molécule · :${m.id}`}
        title={m.label}
        actions={<>
          <button type="button" className="btn btn-ghost" onClick={() => setEditing(true)}><Pencil size={16} aria-hidden="true" /> Modifier</button>
          <button type="button" className="btn btn-danger" onClick={remove}><Trash2 size={16} aria-hidden="true" /> Supprimer</button>
        </>}
      />

      <div className="kpis">
        <div className="kpi"><span className="kpi-label">Code ATC</span><span className="kpi-value mono">{m.codeATC || '—'}</span></div>
        <div className="kpi"><span className="kpi-label">Dose max / jour</span><span className="kpi-value">{m.doseMaxJourMg ? `${m.doseMaxJourMg} mg` : '—'}</span></div>
        <div className="kpi"><span className="kpi-label">Médicaments</span><span className="kpi-value">{m.medicaments.length}</span></div>
        <div className="kpi"><span className="kpi-label">Effets secondaires</span><span className="kpi-value">{m.effets.length}</span></div>
      </div>

      <div className="cards-2">
        <section className="panel">
          <h2 className="panel-title">Classes (rdf:type)</h2>
          <p className="muted small">La classe déclarée est la plus précise ; les classes parentes sont déduites par le raisonneur.</p>
          <ul className="badge-list">
            {m.classes.map((c) => <li key={c.id}><Badge tone={c.inferee ? 'neutral' : 'dark'}>{CLASS_LABELS[c.id] || c.label}</Badge>{c.inferee && <InferredBadge />}</li>)}
          </ul>
        </section>

        <section className="panel">
          <h2 className="panel-title">Contenue dans (estContenuDans)</h2>
          <p className="muted small">Propriété inverse de contientMolecule : aucun triplet n’est déclaré dans ce sens.</p>
          {m.medicaments.length ? (
            <ul className="link-list">
              {m.medicaments.map((x) => <li key={x.id}><Link to={`/medicaments/${x.id}`}>{x.label}</Link><span>{fmtPrix(x.prix)}</span></li>)}
            </ul>
          ) : <Empty>Aucun médicament ne contient cette molécule.</Empty>}
        </section>

        <section className="panel">
          <h2 className="panel-title">Effets secondaires (peutProvoquer)</h2>
          {m.effets.length ? (
            <ul className="link-list">
              {m.effets.map((e) => <li key={e.id}><span>{e.label}</span><span><Badge tone={e.gravite === 'grave' ? 'danger' : 'neutral'}>{e.gravite}</Badge> <span className="muted small">{e.frequence}</span></span></li>)}
            </ul>
          ) : <Empty>Aucun effet renseigné.</Empty>}
        </section>

        <section className="panel">
          <h2 className="panel-title">Contre-indications (aContreIndication)</h2>
          {m.contreIndications.length ? (
            <ul className="link-list">
              {m.contreIndications.map((c) => <li key={c.id}><span>{c.label}{c.pathologie && <span className="muted small"> → {c.pathologie}</span>}</span><Badge tone={c.risque === 'absolu' ? 'danger' : 'gold'}>{c.risque}</Badge></li>)}
            </ul>
          ) : <Empty>Aucune contre-indication renseignée.</Empty>}
        </section>

        <section className="panel">
          <h2 className="panel-title">Interagit avec (propriété symétrique)</h2>
          {m.interactions.length ? (
            <ul className="link-list">
              {m.interactions.map((i) => <li key={i.id}><Link to={`/molecules/${i.id}`}>{i.label}</Link>{i.inferee ? <InferredBadge /> : <Badge>déclarée</Badge>}</li>)}
            </ul>
          ) : <Empty>Aucune interaction connue.</Empty>}
        </section>
      </div>

      <SparqlPanel items={res.sparql} />

      {editing && (
        <MoleculeForm
          initial={m}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            notify('Molécule modifiée (DELETE / INSERT WHERE)');
            res.reload();
          }}
        />
      )}
    </>
  );
}
