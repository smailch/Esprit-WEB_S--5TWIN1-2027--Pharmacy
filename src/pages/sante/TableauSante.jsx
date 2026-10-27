import { Link } from 'react-router-dom';
import { api } from './api';
import { useApi } from './hooks';
import { AlertBanner, Async } from './ui';

function Bars({ items, labelKey, valueKey, href }) {
  const max = Math.max(1, ...items.map((i) => i[valueKey]));
  return (
    <ul className="bars">
      {items.map((i) => (
        <li key={i[labelKey]}>
          {href ? <a href={href(i)}>{i[labelKey]}</a> : <span>{i[labelKey]}</span>}
          <span className="bar" aria-hidden="true"><span style={{ width: `${(i[valueKey] / max) * 100}%` }} /></span>
          <b>{i[valueKey]}</b>
        </li>
      ))}
    </ul>
  );
}

export default function TableauSante() {
  const stats = useApi((signal) => api.stats({ signal }), []);
  const alertes = useApi((signal) => api.alertes({}, { signal }), []);

  return (
    <>
      <h1>Tableau de bord</h1>
      <p className="lead muted">Modules <b>Pathologie</b> et <b>Personne</b> de l&apos;ontologie PharmaSémantique.</p>
      <Async state={stats}>
        {(s) => {
          const c = s.compteurs;
          const cards = [
            ['Patients enfants', c.enfants, 'âge < 18 (classe définie)', '/personnes?tab=patients'],
            ['Patients adultes', c.adultes, 'âge ≥ 18 (classe définie)', '/personnes?tab=patients'],
            ['Maladies aiguës', c.aigues, 'sous-types compris', '/pathologies'],
            ['Maladies chroniques', c.chroniques, 'sous-types compris', '/pathologies'],
            ['Médecins', c.medecins, '', '/personnes?tab=medecins'],
            ['Pharmaciens', c.pharmaciens, '', '/personnes?tab=pharmaciens'],
          ];
          return (
            <>
              <section className="cards" aria-label="Compteurs">
                {cards.map(([label, value, hint, href]) => (
                  <Link key={label} className="card metric" to={href}>
                    <span className="metric-value">{value}</span>
                    <span>{label}</span>
                    {hint && <small className="muted">{hint}</small>}
                  </Link>
                ))}
                <a className={`card metric ${s.alertes ? 'danger' : ''}`} href="#alertes">
                  <span className="metric-value">{s.alertes}</span>
                  <span>Alertes en cours</span>
                </a>
              </section>
              <div className="grid-2">
                <section className="card">
                  <h2>Patients par pathologie</h2>
                  <Bars items={s.patientsParPathologie.slice(0, 10)} labelKey="pathologie" valueKey="nbPatients" />
                </section>
                <section className="card">
                  <h2>Patients par tranche d&apos;âge</h2>
                  <Bars items={s.tranchesAge} labelKey="tranche" valueKey="nb" />
                  <h2 className="mt">Professionnels par spécialité</h2>
                  <Bars items={s.specialites.map((x) => ({ ...x, label: `${x.specialite} (${x.classe})` }))}
                    labelKey="label" valueKey="nb" />
                </section>
              </div>
            </>
          );
        }}
      </Async>
      <section id="alertes" className="mt">
        <h2>Alertes de sécurité</h2>
        <p className="muted small">Contre-indication liée à une pathologie du patient, ou allergie connue à une molécule prescrite (requête SPARQL).</p>
        <Async state={alertes} empty={(d) => !d.length}>
          {(list) => <AlertBanner alertes={list} />}
        </Async>
      </section>
    </>
  );
}
