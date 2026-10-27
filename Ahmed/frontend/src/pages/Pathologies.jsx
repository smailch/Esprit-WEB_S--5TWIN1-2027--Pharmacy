import { useState } from 'react';
import { api } from '../api/client';
import { useApi, useDebounced } from '../hooks';
import { Async, Badge, Empty, ErrorBox, Field, Modal, Pagination } from '../components/ui';

export const TYPES = {
  InfectionAigue: 'Infection aiguë',
  DouleurAigue: 'Douleur aiguë',
  MaladieAigue: 'Maladie aiguë (autre)',
  MaladieMetabolique: 'Maladie métabolique',
  InsuffisanceOrgane: "Insuffisance d'organe",
  MaladieChronique: 'Maladie chronique (autre)',
};
const LIMIT = 10;

function PathologieForm({ initial, onClose, onSaved }) {
  const editing = Boolean(initial);
  const [form, setForm] = useState({ label: initial?.label || '', type: initial?.type || 'InfectionAigue', code: initial?.code || '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = editing
        ? await api.update('pathologies', initial.id, { label: form.label, code: form.code })
        : await api.create('pathologies', form);
      onSaved(res.id || initial.id);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={editing ? `Modifier « ${initial.label} »` : 'Nouvelle pathologie'} onClose={onClose}>
      <form onSubmit={submit} className="form">
        <Field label="Libellé"><input required minLength={2} value={form.label} onChange={set('label')} /></Field>
        <Field label="Type" hint={editing ? 'Le type ne se modifie pas (supprimer puis recréer).' : 'Classe OWL de niveau 3 (aiguë ou chronique).'}>
          <select value={form.type} onChange={set('type')} disabled={editing}>
            {Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
        <Field label="Code CIM-10" hint="Ex. J11, E11, K27.4">
          <input required pattern="[A-Z][0-9]{2}(\.[0-9]{1,2})?" value={form.code} onChange={set('code')} />
        </Field>
        <ErrorBox error={error} />
        <div className="actions">
          <button type="button" className="btn" onClick={onClose}>Annuler</button>
          <button className="btn primary" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer'}</button>
        </div>
      </form>
    </Modal>
  );
}

function Detail({ id, onEdit, onDeleted }) {
  const d = useApi((signal) => api.get('pathologies', id, { signal }), [id]);
  const [error, setError] = useState(null);
  const remove = async () => {
    if (!window.confirm('Supprimer cette pathologie ?')) return;
    try {
      await api.remove('pathologies', id);
      onDeleted();
    } catch (err) {
      setError(err);
    }
  };
  return (
    <Async state={d}>
      {(p) => (
        <aside className="card detail" aria-label={`Détail ${p.label}`}>
          <h2>{p.label}</h2>
          <p><Badge tone={p.famille === 'MaladieAigue' ? 'gold' : 'green'}>{p.famille === 'MaladieAigue' ? 'Aiguë' : 'Chronique'}</Badge>{' '}
            <Badge>{TYPES[p.type] || p.type}</Badge> <code>{p.code}</code></p>
          <h3>Médicaments indiqués</h3>
          {p.indiques.length ? <ul className="chips">{p.indiques.map((m) => <li key={m.id}>{m.label}</li>)}</ul> : <Empty>Aucun.</Empty>}
          <h3>Médicaments contre-indiqués</h3>
          {p.contreIndiques.length ? (
            <ul className="chips danger">{p.contreIndiques.map((m) => <li key={m.id} title={`via ${m.via}`}>{m.label} <small>({m.via})</small></li>)}</ul>
          ) : <Empty>Aucun.</Empty>}
          <h3>Patients concernés</h3>
          {p.patients.length ? (
            <ul className="chips">{p.patients.map((x) => <li key={x.id}><a href={`#/patients/${x.id}`}>{x.label}</a></li>)}</ul>
          ) : <Empty>Aucun patient.</Empty>}
          <ErrorBox error={error} />
          <div className="actions">
            <a className="btn" href={`#/graphe/${id}`}>Graphe</a>
            <button className="btn" onClick={() => onEdit(p)}>Modifier</button>
            <button className="btn danger" onClick={remove}>Supprimer</button>
          </div>
        </aside>
      )}
    </Async>
  );
}

export default function Pathologies() {
  const [q, setQ] = useState('');
  const [filtre, setFiltre] = useState('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(null); // null | 'new' | objet
  const dq = useDebounced(q);
  const famille = ['MaladieAigue', 'MaladieChronique'].includes(filtre) ? filtre : undefined;
  const type = famille ? undefined : filtre || undefined;
  const list = useApi((signal) => api.list('pathologies', { q: dq, famille, type, limit: LIMIT, offset }, { signal }),
    [dq, filtre, offset]);

  return (
    <>
      <div className="page-head">
        <h1>Pathologies</h1>
        <button className="btn primary" onClick={() => setForm('new')}>+ Nouvelle pathologie</button>
      </div>
      <div className="toolbar">
        <label className="sr-only" htmlFor="q-patho">Rechercher</label>
        <input id="q-patho" type="search" placeholder="Rechercher (libellé, code CIM-10)…" value={q}
          onChange={(e) => { setQ(e.target.value); setOffset(0); }} />
        <label className="sr-only" htmlFor="f-patho">Filtrer par type</label>
        <select id="f-patho" value={filtre} onChange={(e) => { setFiltre(e.target.value); setOffset(0); }}>
          <option value="">Tous les types</option>
          <option value="MaladieAigue">Aiguës (tous sous-types)</option>
          <option value="MaladieChronique">Chroniques (tous sous-types)</option>
          {['InfectionAigue', 'DouleurAigue', 'MaladieMetabolique', 'InsuffisanceOrgane'].map((t) => (
            <option key={t} value={t}>{TYPES[t]}</option>
          ))}
        </select>
      </div>
      <div className={selected ? 'split' : ''}>
        <Async state={list} empty={(d) => !d.items.length}>
          {(data) => (
            <div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th scope="col">Pathologie</th><th scope="col">CIM-10</th><th scope="col">Type</th><th scope="col">Patients</th></tr></thead>
                  <tbody>
                    {data.items.map((p) => (
                      <tr key={p.id} className={selected === p.id ? 'selected' : ''}>
                        <td><button className="link-btn" onClick={() => setSelected(p.id)}>{p.label}</button></td>
                        <td><code>{p.code}</code></td>
                        <td><Badge tone={p.famille === 'MaladieAigue' ? 'gold' : 'green'}>{p.famille === 'MaladieAigue' ? 'Aiguë' : 'Chronique'}</Badge> {TYPES[p.type] || p.type}</td>
                        <td>{p.nbPatients}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
            </div>
          )}
        </Async>
        {selected && (
          <Detail key={selected} id={selected} onEdit={setForm}
            onDeleted={() => { setSelected(null); list.reload(); }} />
        )}
      </div>
      {form && (
        <PathologieForm initial={form === 'new' ? null : form} onClose={() => setForm(null)}
          onSaved={(id) => { setForm(null); setSelected(null); list.reload(); setTimeout(() => setSelected(id)); }} />
      )}
    </>
  );
}
