import { Fragment } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertTriangle, ShieldCheck, ArrowRight, User, ClipboardList, Pill, FlaskConical, Ban, HeartPulse, Stethoscope } from 'lucide-react';
import { apiD } from '../api/moduleD.js';
import { useApi } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge } from '../app/ui.jsx';
import { fmtDate } from './Prescriptions.jsx';
import { DONNEE_LABELS, valeurDonnee } from './DonneesCliniques.jsx';
import '../app/moduleD.css';

const STEPS = [
  { label: 'Patient', icon: User }, { label: 'Prescription', icon: ClipboardList }, { label: 'Médicament', icon: Pill },
  { label: 'Molécule', icon: FlaskConical }, { label: 'Contre-indication', icon: Ban }, { label: 'Pathologie', icon: HeartPulse },
];
const ALERT_TONES = { 'contre-indication': 'danger', antécédent: 'danger', allergie: 'gold', analyse: 'gold' };

function Node({ kind, children, to, danger, muted }) {
  const cls = `chain-node ${danger ? 'is-danger' : ''} ${muted ? 'is-muted' : ''}`;
  const { icon: Icon } = STEPS.find((s) => s.label === kind);
  const body = <><Icon size={15} aria-hidden="true" /><span>{children}</span></>;
  return to ? <Link to={to} className={cls}>{body}</Link> : <span className={cls}>{body}</span>;
}

const Arrow = ({ label }) => <span className="chain-arrow" title={label}><ArrowRight size={14} aria-hidden="true" /><span className="chain-rel">{label}</span></span>;

function Chain({ data }) {
  const { patient } = data;
  if (!data.prescriptions.length) return <Empty>Ce patient n’a aucune prescription.</Empty>;
  const rows = data.prescriptions.flatMap((pr) => pr.medicaments.flatMap((med) => med.molecules.flatMap((mol) => (
    (mol.contreIndications.length ? mol.contreIndications : [null]).map((ci, k) => ({ pr, med, mol, ci, key: `${pr.id}-${med.id}-${mol.id}-${k}` }))
  ))));
  return (
    <div className="chain">
      {rows.map(({ pr, med, mol, ci, key }) => (
        <div key={key} className={`chain-row ${ci?.conflit || mol.allergie ? 'is-danger' : ''}`}>
          <Node kind="Patient">{patient.label}</Node>
          <Arrow label="aPrescription" />
          <Node kind="Prescription" to={`/prescriptions/${pr.id}`}>{pr.id}</Node>
          <Arrow label="prescritMedicament" />
          <Node kind="Médicament" to={`/medicaments/${med.id}`}>{med.label}</Node>
          <Arrow label="contientMolecule" />
          <Node kind="Molécule" to={`/molecules/${mol.id}`} danger={mol.allergie}>{mol.label}{mol.allergie && ' · allergie connue'}</Node>
          {ci ? (
            <>
              <Arrow label="aContreIndication" />
              <Node kind="Contre-indication" danger={ci.conflit}>{ci.label}{ci.risque && <Badge tone={ci.risque === 'absolu' ? 'danger' : 'gold'}>{ci.risque}</Badge>}</Node>
              {ci.pathologie && (
                <>
                  <Arrow label="concernePathologie" />
                  <Node kind="Pathologie" danger={ci.conflit} muted={!ci.conflit}>
                    {ci.pathologie.label}{ci.conflit ? ' — présente dans le dossier' : ''}
                  </Node>
                </>
              )}
            </>
          ) : <span className="muted small">aucune contre-indication déclarée</span>}
        </div>
      ))}
    </div>
  );
}

export default function Scenario() {
  const [params, setParams] = useSearchParams();
  const ref = useApi(() => apiD.referentiels(), []);
  const alertes = useApi(() => apiD.alertes(), []);
  const pid = params.get('patient') || 'Patient_Youssef';
  const dossier = useApi(() => apiD.dossier(pid), [pid]);
  const d = dossier.data;

  return (
    <>
      <PageHeader eyebrow="Module D · Scénario de démonstration" title="Dossier patient : prescriptions et données cliniques">
        <p>Les ordonnances (<code>concernePatient</code> → <code>prescritMedicament</code> → <code>contientMolecule</code> → <code>aContreIndication</code> → <code>concernePathologie</code>) sont confrontées au dossier clinique du patient : pathologies (<code>souffreDe</code>), allergies (<code>allergiqueA</code>), antécédents (<code>porteSur</code>) et analyses (clairance de la créatinine).</p>
      </PageHeader>

      <div className="filter-bar">
        <span className="muted small">Patient :</span>
        {(ref.data?.patients || []).map((p) => (
          <button key={p.id} type="button" className={`chip ${pid === p.id ? 'is-active' : ''}`} aria-pressed={pid === p.id} onClick={() => setParams({ patient: p.id })}>
            {p.label}
          </button>
        ))}
      </div>

      <ErrorBox message={dossier.error} onRetry={dossier.reload} />
      {dossier.loading && !d ? <Loading /> : d && (
        <>
          <div className={`verdict ${d.danger ? 'is-ko' : 'is-ok'}`} role="status">
            {d.danger ? <AlertTriangle size={20} aria-hidden="true" /> : <ShieldCheck size={20} aria-hidden="true" />}
            <span>
              <strong>{d.patient.label}</strong> ({d.patient.age} ans) — pathologies : {d.patient.pathologies.map((p) => p.label).join(', ') || 'aucune'}
              <br />
              {d.danger
                ? <>{d.alertes.length} alerte{d.alertes.length > 1 ? 's' : ''} sur les prescriptions{d.contreIndicationDetectee ? ' (ASK sur la chaîne de contre-indication : VRAI)' : ''}.</>
                : 'Aucune contre-indication, allergie, antécédent ou analyse à risque : les prescriptions sont compatibles avec le dossier.'}
            </span>
          </div>

          {d.alertes.length > 0 && (
            <div className="alerts">
              {d.alertes.map((a, i) => (
                <div key={i} className="alert alert-interaction" role="alert">
                  <AlertTriangle size={20} aria-hidden="true" />
                  <div>
                    <p className="alert-kind">{a.type}</p>
                    <p><Link to={`/prescriptions/${a.prescription.id}`}>{a.prescription.id}</Link> · <strong>{a.medicament.label}</strong> ({a.molecule.label}) — {a.motif}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <section className="panel">
            <h2 className="panel-title"><Stethoscope size={15} aria-hidden="true" /> Données cliniques (aDonneeClinique)</h2>
            {d.donneesCliniques.length ? (
              <ul className="link-list">
                {d.donneesCliniques.map((x) => (
                  <li key={x.id}>
                    <span>{x.label} <Badge tone={x.categorie === 'ExamenClinique' ? 'neutral' : 'gold'}>{DONNEE_LABELS[x.type]}</Badge></span>
                    <span className="small">{valeurDonnee(x)} · {fmtDate(x.dateMesure)}</span>
                  </li>
                ))}
              </ul>
            ) : <Empty>Aucune donnée clinique : <Link to="/donnees-cliniques">en ajouter une</Link>.</Empty>}
          </section>

          <div className="chain-legend" aria-hidden="true">
            {STEPS.map((s, i) => <Fragment key={s.label}>{i > 0 && <ArrowRight size={12} />}<span><s.icon size={13} /> {s.label}</span></Fragment>)}
          </div>
          <section className="panel"><Chain data={d} /></section>
        </>
      )}

      <section className="panel">
        <h2 className="panel-title"><AlertTriangle size={15} aria-hidden="true" /> Toutes les alertes (pathologie, allergie, antécédent, analyse)</h2>
        <ErrorBox message={alertes.error} />
        {alertes.loading && !alertes.data ? <Loading /> : !alertes.data?.length ? <Empty>Aucune alerte.</Empty> : (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th scope="col">Ordonnance</th><th scope="col">Patient</th><th scope="col">Médicament (molécule)</th><th scope="col">Source</th><th scope="col">Motif</th></tr></thead>
              <tbody>
                {alertes.data.map((a, i) => (
                  <tr key={i}>
                    <th scope="row"><Link to={`/prescriptions/${a.prescription.id}`}>{a.prescription.id}</Link></th>
                    <td><button type="button" className="btn-link" onClick={() => setParams({ patient: a.patient.id })}>{a.patient.label}</button></td>
                    <td>{a.medicament.label} ({a.molecule.label})</td>
                    <td><Badge tone={ALERT_TONES[a.type]}>{a.type}</Badge></td>
                    <td>{a.motif}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <SparqlPanel items={[...dossier.sparql, ...alertes.sparql]} />
    </>
  );
}
