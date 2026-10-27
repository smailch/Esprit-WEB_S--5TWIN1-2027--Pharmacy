import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { api } from './api';
import { download, useApi } from './hooks';
import { AlertBanner, Async, ClasseBadge, Empty, ErrorBox } from './ui';
import { PatientForm, usePathologyOptions } from './Personnes';

export default function PatientFiche({ id }) {
  const go = useNavigate();
  const p = useApi((signal) => api.get('patients', id, { signal }), [id]);
  const pathos = usePathologyOptions();
  const [add, setAdd] = useState('');
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState(null);

  const act = async (fn) => {
    setError(null);
    try {
      await fn();
      p.reload();
    } catch (err) {
      setError(err);
    }
  };
  const remove = async () => {
    if (!window.confirm('Supprimer ce patient ?')) return;
    setError(null);
    try {
      await api.remove('patients', id);
      go('/personnes?tab=patients');
    } catch (err) {
      setError(err);
    }
  };
  const exportTurtle = async () => download(`${id}.ttl`, await api.patientRdf(id), 'text/turtle');

  return (
    <Async state={p}>
      {(pat) => {
        const owned = new Set(pat.pathologies.map((x) => x.id));
        return (
          <>
            <p><Link to="/personnes?tab=patients">← Patients</Link></p>
            <div className="page-head">
              <h1>{pat.label}</h1>
              <div className="actions">
                <button className="btn" onClick={exportTurtle}>Export Turtle</button>
                <button className="btn" onClick={() => setEditing(true)}>Modifier</button>
                <button className="btn danger" onClick={remove}>Supprimer</button>
              </div>
            </div>
            <AlertBanner alertes={pat.alertes} />
            <ErrorBox error={error} />
            <div className="grid-2">
              <section className="card">
                <h2>Informations</h2>
                <dl className="info">
                  <dt>URI</dt><dd><code>:{id}</code></dd>
                  <dt>Nom</dt><dd>{pat.nom}</dd>
                  <dt>Âge</dt><dd>{pat.age} ans</dd>
                  <dt>Sexe</dt><dd>{pat.sexe}</dd>
                  <dt>Classe</dt><dd><ClasseBadge classe={pat.classe} asserte={pat.asserte} /></dd>
                </dl>
                <p className="muted small">
                  {pat.asserte
                    ? 'Classe écrite dans les données (assertée), cohérente avec l’âge.'
                    : 'Seule la classe :Patient est écrite : Enfant/Adulte est déduit de l’âge (classe définie OWL, confirmée par HermiT).'}
                </p>
              </section>
              <section className="card">
                <h2>Pathologies</h2>
                {pat.pathologies.length ? (
                  <ul className="list">
                    {pat.pathologies.map((x) => (
                      <li key={x.id}>
                        <span>{x.label} <code>{x.code}</code> <small className="muted">{x.famille === 'MaladieAigue' ? 'aiguë' : 'chronique'}</small></span>
                        <button className="btn small" aria-label={`Retirer ${x.label}`}
                          onClick={() => act(() => api.removePathology(id, x.id))}>Retirer</button>
                      </li>
                    ))}
                  </ul>
                ) : <Empty>Aucune pathologie.</Empty>}
                <form className="toolbar" onSubmit={(e) => { e.preventDefault(); if (add) act(() => api.addPathology(id, add)).then(() => setAdd('')); }}>
                  <label className="sr-only" htmlFor="add-patho">Ajouter une pathologie</label>
                  <select id="add-patho" value={add} onChange={(e) => setAdd(e.target.value)}>
                    <option value="">Ajouter une pathologie…</option>
                    {pathos.data?.items.filter((x) => !owned.has(x.id)).map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
                  </select>
                  <button className="btn primary" disabled={!add}>Ajouter</button>
                </form>
              </section>
            </div>
            <section className="card mt">
              <h2>Prescriptions <small className="muted">(lecture seule — module Prescription)</small></h2>
              {pat.prescriptions.length ? (
                <div className="table-wrap">
                  <table>
                    <thead><tr><th scope="col">Ordonnance</th><th scope="col">Date</th><th scope="col">Médicaments</th><th scope="col">Médecin</th><th scope="col">Pharmacien</th></tr></thead>
                    <tbody>
                      {pat.prescriptions.map((x) => (
                        <tr key={x.id} className={pat.alertes.some((a) => a.prescId === x.id) ? 'row-danger' : ''}>
                          <td>{x.label}</td><td>{x.date}</td><td>{x.medicaments}</td>
                          <td>{x.medecin || '—'}</td>
                          <td>{x.pharmacien || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <Empty>Aucune prescription.</Empty>}
            </section>
            {editing && (
              <PatientForm initial={{ ...pat, id }} onClose={() => setEditing(false)}
                onSaved={() => { setEditing(false); p.reload(); }} />
            )}
          </>
        );
      }}
    </Async>
  );
}
