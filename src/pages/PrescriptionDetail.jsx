import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Pencil, Trash2, AlertTriangle, ShieldCheck, Route } from 'lucide-react';
import { apiD } from '../api/moduleD.js';
import { useApi } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, InferredBadge } from '../app/ui.jsx';
import { PrescriptionForm } from '../app/formsModuleD.jsx';
import LayerGraph from '../app/LayerGraph.jsx';
import { useToast } from '../app/Toast.jsx';
import { TYPE_LABELS, fmtDate } from './Prescriptions.jsx';
import { DONNEE_LABELS, valeurDonnee } from './DonneesCliniques.jsx';
import '../app/moduleD.css';

export default function PrescriptionDetail() {
  const { id } = useParams();
  const res = useApi(() => apiD.prescription(id), [id]);
  const graph = useApi(() => apiD.prescriptionGraphe(id), [id]);
  const [editing, setEditing] = useState(false);
  const navigate = useNavigate();
  const notify = useToast();
  const p = res.data;

  const remove = async () => {
    if (!window.confirm(`Supprimer définitivement ${p.label} ?`)) return;
    try {
      await apiD.deletePrescription(id);
      notify(`${p.label} supprimée (DELETE WHERE)`);
      navigate('/prescriptions');
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  if (res.loading && !p) return <Loading />;
  if (res.error) return <><Link to="/prescriptions" className="back"><ArrowLeft size={16} /> Prescriptions</Link><ErrorBox message={res.error} /></>;

  return (
    <>
      <Link to="/prescriptions" className="back"><ArrowLeft size={16} aria-hidden="true" /> Prescriptions</Link>
      <PageHeader
        eyebrow={`Prescription · :${p.id}`}
        title={p.label}
        actions={<>
          <button type="button" className="btn btn-ghost" onClick={() => setEditing(true)}><Pencil size={16} aria-hidden="true" /> Modifier</button>
          <button type="button" className="btn btn-danger" onClick={remove}><Trash2 size={16} aria-hidden="true" /> Supprimer</button>
        </>}
      >
        <ul className="badge-list">
          {p.classes.map((c) => <li key={c.id}><Badge tone={c.inferee ? 'neutral' : 'dark'}>{c.label}</Badge>{c.inferee && <InferredBadge />}</li>)}
        </ul>
      </PageHeader>

      <div className="kpis">
        <div className="kpi"><span className="kpi-label">Date (xsd:date)</span><span className="kpi-value">{fmtDate(p.datePrescription)}</span></div>
        <div className="kpi"><span className="kpi-label">Durée</span><span className="kpi-value">{p.dureeJours} jours</span></div>
        <div className="kpi"><span className="kpi-label">Type déclaré</span><span className="kpi-value">{TYPE_LABELS[p.type] || '—'}</span></div>
        <div className="kpi"><span className="kpi-label">Renouvelable</span><span className="kpi-value">{p.estRenouvelable ? 'Oui' : 'Non'}</span></div>
      </div>

      {p.alertes.length > 0 ? (
        <div className="alerts">
          {p.alertes.map((a, i) => (
            <div key={i} className="alert alert-interaction" role="alert">
              <AlertTriangle size={20} aria-hidden="true" />
              <div>
                <p className="alert-kind">{a.type}</p>
                <p><strong>{a.medicament.label}</strong> ({a.molecule.label}) pour {a.patient.label} — {a.motif}</p>
              </div>
            </div>
          ))}
          <Link to={`/scenario?patient=${p.patient?.id}`} className="btn-link"><Route size={14} aria-hidden="true" /> Voir la chaîne complète du patient</Link>
        </div>
      ) : (
        <p className="verdict is-ok"><ShieldCheck size={18} aria-hidden="true" /> Aucune contre-indication ni allergie détectée pour ce patient.</p>
      )}

      <div className="cards-2">
        <section className="panel">
          <h2 className="panel-title">Patient (concernePatient)</h2>
          {p.patient ? (
            <ul className="link-list">
              <li><Link to={`/scenario?patient=${p.patient.id}`}>{p.patient.label}</Link><span className="muted small">{p.patient.age} ans · {p.patient.sexe}</span></li>
              <li><span>Pathologies (souffreDe)</span><span className="small">{p.patient.pathologies.join(', ') || '—'}</span></li>
            </ul>
          ) : <Empty />}
        </section>

        <section className="panel">
          <h2 className="panel-title">Prescripteur et délivrance</h2>
          <ul className="link-list">
            <li><span>Médecin (prescritPar)</span><span>{p.medecin ? `${p.medecin.label}${p.medecin.specialite ? ` — ${p.medecin.specialite}` : ''}` : '—'}</span></li>
            <li><span>Pharmacien (estDelivreePar)</span>{p.pharmacien ? <span>{p.pharmacien.label}</span> : <Badge tone="gold">pas encore délivrée</Badge>}</li>
            <li><span>Posologie</span><span>{p.posologie}</span></li>
          </ul>
        </section>
      </div>

      <section className="panel">
        <h2 className="panel-title">Dossier clinique du patient (aDonneeClinique)</h2>
        {p.patient?.donneesCliniques.length ? (
          <ul className="link-list">
            {p.patient.donneesCliniques.map((d) => (
              <li key={d.id}>
                <span>{d.label} <Badge tone={d.categorie === 'ExamenClinique' ? 'neutral' : 'gold'}>{DONNEE_LABELS[d.type]}</Badge></span>
                <span className="small">{valeurDonnee(d)} · {fmtDate(d.dateMesure)}</span>
              </li>
            ))}
          </ul>
        ) : <Empty>Aucune donnée clinique enregistrée pour ce patient.</Empty>}
      </section>

      <section className="panel">
        <h2 className="panel-title">Médicaments prescrits (prescritMedicament)</h2>
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th scope="col">Médicament</th><th scope="col">Dosage</th><th scope="col">Forme galénique</th><th scope="col">Molécules</th></tr></thead>
            <tbody>
              {p.medicaments.map((m) => (
                <tr key={m.id}>
                  <th scope="row"><Link to={`/medicaments/${m.id}`}>{m.label}</Link></th>
                  <td>{m.dosage || '—'}</td>
                  <td>{m.forme || '—'}</td>
                  <td>{m.molecules.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title">Graphe de l’ordonnance (requête CONSTRUCT · {graph.data?.triplets ?? '…'} triplets)</h2>
        <ErrorBox message={graph.error} />
        {graph.loading && !graph.data ? <Loading /> : <LayerGraph data={graph.data} />}
      </section>

      <SparqlPanel items={[...res.sparql, ...graph.sparql]} />

      {editing && (
        <PrescriptionForm
          initial={p}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            notify('Prescription modifiée (DELETE / INSERT WHERE)');
            res.reload(); graph.reload();
          }}
        />
      )}
    </>
  );
}
