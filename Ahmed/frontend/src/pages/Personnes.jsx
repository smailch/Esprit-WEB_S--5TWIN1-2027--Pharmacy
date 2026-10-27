import { useState } from 'react';
import { api } from '../api/client';
import { go, useApi, useDebounced } from '../hooks';
import { Async, ClasseBadge, ErrorBox, Field, Modal, Pagination } from '../components/ui';

const LIMIT = 10;
const TABS = [['patients', 'Patients'], ['medecins', 'Médecins'], ['pharmaciens', 'Pharmaciens']];

export function usePathologyOptions() {
  return useApi((signal) => api.list('pathologies', { limit: 100 }, { signal }), []);
}

export function PatientForm({ initial, onClose, onSaved }) {
  const editing = Boolean(initial);
  const pathos = usePathologyOptions();
  const [form, setForm] = useState(
    initial ? { label: initial.label, nom: initial.nom || '', age: initial.age, sexe: initial.sexe || 'F' }
      : { prenom: '', nom: '', age: '', sexe: 'F', pathologies: [] },
  );
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const age = Number(form.age);

  const toggle = (id) => setForm({
    ...form, pathologies: form.pathologies.includes(id) ? form.pathologies.filter((x) => x !== id) : [...form.pathologies, id],
  });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = { ...form, age };
      const res = editing ? await api.update('patients', initial.id, body) : await api.create('patients', body);
      onSaved(res.id);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={editing ? `Modifier ${initial.label}` : 'Nouveau patient'} onClose={onClose}>
      <form onSubmit={submit} className="form">
        {editing ? (
          <Field label="Nom complet affiché (rdfs:label)"><input required value={form.label} onChange={set('label')} /></Field>
        ) : (
          <Field label="Prénom" hint="L'URI sera Patient_<Prénom> (sans accents)."><input required value={form.prenom} onChange={set('prenom')} /></Field>
        )}
        <Field label="Nom de famille"><input required value={form.nom} onChange={set('nom')} /></Field>
        <div className="row">
          <Field label="Âge" hint={form.age !== '' ? `Classe dérivée : ${age < 18 ? 'PatientEnfant' : 'PatientAdulte'}` : '0 à 120 ans'}>
            <input required type="number" min="0" max="120" value={form.age} onChange={set('age')} />
          </Field>
          <Field label="Sexe">
            <select value={form.sexe} onChange={set('sexe')}><option value="F">F</option><option value="M">M</option></select>
          </Field>
        </div>
        {!editing && (
          <fieldset className="field">
            <legend>Pathologies (souffreDe)</legend>
            <Async state={pathos}>
              {(d) => (
                <div className="checks">
                  {d.items.map((p) => (
                    <label key={p.id}><input type="checkbox" checked={form.pathologies.includes(p.id)} onChange={() => toggle(p.id)} /> {p.label}</label>
                  ))}
                </div>
              )}
            </Async>
          </fieldset>
        )}
        <ErrorBox error={error} />
        <div className="actions">
          <button type="button" className="btn" onClick={onClose}>Annuler</button>
          <button className="btn primary" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer'}</button>
        </div>
      </form>
    </Modal>
  );
}

function Patients() {
  const [f, setF] = useState({ q: '', sexe: '', classe: '', age_min: '', age_max: '', pathologie: '' });
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const pathos = usePathologyOptions();
  const dq = useDebounced(f.q);
  const params = { ...f, q: dq, limit: LIMIT, offset };
  const list = useApi((signal) => api.list('patients', params, { signal }), [JSON.stringify(params)]);
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setOffset(0); };

  return (
    <>
      <div className="toolbar">
        <input type="search" aria-label="Rechercher un patient" placeholder="Rechercher un patient…" value={f.q} onChange={set('q')} />
        <select aria-label="Sexe" value={f.sexe} onChange={set('sexe')}>
          <option value="">Sexe</option><option value="F">F</option><option value="M">M</option>
        </select>
        <select aria-label="Classe" value={f.classe} onChange={set('classe')}>
          <option value="">Enfant / adulte</option><option value="PatientEnfant">Enfants</option><option value="PatientAdulte">Adultes</option>
        </select>
        <input type="number" aria-label="Âge minimum" placeholder="Âge min" min="0" max="120" value={f.age_min} onChange={set('age_min')} />
        <input type="number" aria-label="Âge maximum" placeholder="Âge max" min="0" max="120" value={f.age_max} onChange={set('age_max')} />
        <select aria-label="Pathologie" value={f.pathologie} onChange={set('pathologie')}>
          <option value="">Toutes pathologies</option>
          {pathos.data?.items.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
        <button className="btn primary" onClick={() => setCreating(true)}>+ Nouveau patient</button>
      </div>
      <Async state={list} empty={(d) => !d.items.length}>
        {(data) => (
          <>
            <div className="table-wrap">
              <table>
                <thead><tr><th scope="col">Patient</th><th scope="col">Âge</th><th scope="col">Sexe</th><th scope="col">Classe</th><th scope="col">Pathologies</th></tr></thead>
                <tbody>
                  {data.items.map((p) => (
                    <tr key={p.id}>
                      <td><a href={`#/patients/${p.id}`}>{p.label}</a></td>
                      <td>{p.age}</td>
                      <td>{p.sexe}</td>
                      <td><ClasseBadge classe={p.classe} asserte={p.asserte} /></td>
                      <td>{p.nbPathologies}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Async>
      {creating && <PatientForm onClose={() => setCreating(false)} onSaved={(id) => go(`/patients/${id}`)} />}
    </>
  );
}

function ProForm({ resource, initial, onClose, onSaved }) {
  const [form, setForm] = useState({ label: initial?.label || '', nom: initial?.nom || '', specialite: initial?.specialite || '' });
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    try {
      const body = { ...form, label: form.label || undefined };
      if (initial) await api.update(resource, initial.id, body);
      else await api.create(resource, body);
      onSaved();
    } catch (err) {
      setError(err);
    }
  };
  const what = resource === 'medecins' ? 'médecin' : 'pharmacien';
  return (
    <Modal title={initial ? `Modifier ${initial.label}` : `Nouveau ${what}`} onClose={onClose}>
      <form onSubmit={submit} className="form">
        <Field label="Nom" hint={initial ? '' : `L'URI sera ${resource === 'medecins' ? 'Dr_' : 'Ph_'}<Nom>.`}>
          <input required value={form.nom} onChange={set('nom')} />
        </Field>
        <Field label="Libellé affiché" hint="Facultatif (par défaut « Dr Nom » / « Pharmacien Nom »)">
          <input value={form.label} onChange={set('label')} />
        </Field>
        <Field label="Spécialité"><input required value={form.specialite} onChange={set('specialite')}
          list="specialites" /></Field>
        <datalist id="specialites">
          {['Médecine générale', 'Pneumologie', 'Pédiatrie', 'Cardiologie', 'Endocrinologie', 'Officine', 'Hôpital'].map((s) => <option key={s} value={s} />)}
        </datalist>
        <ErrorBox error={error} />
        <div className="actions">
          <button type="button" className="btn" onClick={onClose}>Annuler</button>
          <button className="btn primary">Enregistrer</button>
        </div>
      </form>
    </Modal>
  );
}

function Professionnels({ resource }) {
  const [q, setQ] = useState('');
  const [offset, setOffset] = useState(0);
  const [form, setForm] = useState(null);
  const [error, setError] = useState(null);
  const dq = useDebounced(q);
  const list = useApi((signal) => api.list(resource, { q: dq, limit: LIMIT, offset }, { signal }), [resource, dq, offset]);

  const remove = async (p) => {
    if (!window.confirm(`Supprimer ${p.label} ?`)) return;
    setError(null);
    try {
      await api.remove(resource, p.id);
      list.reload();
    } catch (err) {
      setError(err);
    }
  };

  return (
    <>
      <div className="toolbar">
        <input type="search" aria-label="Rechercher" placeholder="Rechercher (nom, spécialité)…" value={q}
          onChange={(e) => { setQ(e.target.value); setOffset(0); }} />
        <button className="btn primary" onClick={() => setForm('new')}>+ Nouveau</button>
      </div>
      <ErrorBox error={error} />
      <Async state={list} empty={(d) => !d.items.length}>
        {(data) => (
          <>
            <div className="table-wrap">
              <table>
                <thead><tr><th scope="col">Nom</th><th scope="col">Spécialité</th><th scope="col">Ordonnances</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  {data.items.map((p) => (
                    <tr key={p.id}>
                      <td><a href={`#/graphe/${p.id}`}>{p.label}</a></td>
                      <td>{p.specialite}</td>
                      <td>{p.nbPrescriptions}</td>
                      <td className="row-actions">
                        <button className="btn small" onClick={() => setForm(p)}>Modifier</button>
                        <button className="btn small danger" onClick={() => remove(p)}>Supprimer</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Async>
      {form && (
        <ProForm resource={resource} initial={form === 'new' ? null : form} onClose={() => setForm(null)}
          onSaved={() => { setForm(null); list.reload(); }} />
      )}
    </>
  );
}

export default function Personnes({ tab }) {
  return (
    <>
      <h1>Personnes</h1>
      <div className="tabs" role="tablist" aria-label="Type de personne">
        {TABS.map(([key, label]) => (
          <a key={key} role="tab" aria-selected={tab === key} href={`#/personnes?tab=${key}`}>{label}</a>
        ))}
      </div>
      <div role="tabpanel">
        {tab === 'patients' ? <Patients /> : <Professionnels key={tab} resource={tab} />}
      </div>
    </>
  );
}
