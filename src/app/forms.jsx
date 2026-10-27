import { useState } from 'react';
import { Save } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from './useApi.js';
import { ChipSelect, ErrorBox, Loading, Modal, CLASS_LABELS } from './ui.jsx';

function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

/* =========================== Molécule =========================== */
export function MoleculeForm({ initial, onClose, onSaved }) {
  const ref = useApi(() => api.referentiels(), []);
  const editing = Boolean(initial);
  const [form, setForm] = useState(() => ({
    nom: initial?.label || '',
    classe: initial?.classe || 'AntalgiqueNonOpioide',
    codeATC: initial?.codeATC || '',
    doseMaxJourMg: initial?.doseMaxJourMg ?? '',
    effets: initial?.effets?.map((e) => e.id) || [],
    contreIndications: initial?.contreIndications?.map((c) => c.id) || [],
    // Seules les interactions déclarées sont éditables (les inférées découlent de la symétrie).
    interactions: initial?.interactions?.filter((i) => !i.inferee).map((i) => i.id) || [],
  }));
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const body = {
      ...form,
      codeATC: form.codeATC.trim().toUpperCase() || null,
      doseMaxJourMg: form.doseMaxJourMg === '' ? null : Number(form.doseMaxJourMg),
    };
    try {
      const res = editing ? await api.updateMolecule(initial.id, body) : await api.createMolecule(body);
      onSaved(res);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const r = ref.data;
  return (
    <Modal title={editing ? `Modifier ${initial.label}` : 'Nouvelle molécule'} onClose={onClose} wide>
      {ref.loading && <Loading />}
      <ErrorBox message={ref.error} />
      {r && (
        <form className="form" onSubmit={submit}>
          <div className="form-grid">
            <Field label="Nom *" hint={editing ? 'L’identifiant (URI) ne change pas.' : 'Devient l’URI : « Naproxène » → :Naproxene'}>
              <input className="input" required minLength={2} maxLength={80} value={form.nom} onChange={set('nom')} />
            </Field>
            <Field label="Classe *" hint="Les classes parentes seront déduites par le raisonneur.">
              <select className="input" value={form.classe} onChange={set('classe')}>
                {r.classesMolecule.map((c) => <option key={c.id} value={c.id}>{CLASS_LABELS[c.id] || c.label}</option>)}
              </select>
            </Field>
            <Field label="Code ATC" hint="Format : lettre, 2 chiffres, 2 lettres, 2 chiffres (ex. M01AE02)">
              <input className="input" pattern="[A-Za-z]\d{2}[A-Za-z]{2}\d{2}" maxLength={7} value={form.codeATC} onChange={set('codeATC')} />
            </Field>
            <Field label="Dose maximale / jour (mg)">
              <input className="input" type="number" min="1" step="any" value={form.doseMaxJourMg} onChange={set('doseMaxJourMg')} />
            </Field>
          </div>
          <ChipSelect label="Effets secondaires (peutProvoquer)" options={r.effets} value={form.effets} onChange={set('effets')} />
          <ChipSelect label="Contre-indications (aContreIndication)" options={r.contreIndications} value={form.contreIndications} onChange={set('contreIndications')} />
          <ChipSelect
            label="Interagit avec (propriété symétrique)"
            options={r.molecules.filter((m) => m.id !== initial?.id)}
            value={form.interactions}
            onChange={set('interactions')}
          />
          <ErrorBox message={error} />
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={saving}><Save size={16} aria-hidden="true" /> {saving ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      )}
    </Modal>
  );
}

/* =========================== Médicament =========================== */
export function MedicamentForm({ initial, onClose, onSaved }) {
  const ref = useApi(() => api.referentiels(), []);
  const editing = Boolean(initial);
  const declaredType = initial?.classes?.some((c) => !c.inferee && c.id.startsWith('Generique')) ? 'Generique' : 'Princeps';
  const [form, setForm] = useState(() => ({
    nomCommercial: initial?.nomCommercial || '',
    type: initial ? declaredType : 'Generique',
    dosage: initial?.dosage || '',
    formeGalenique: initial?.formeGalenique || 'comprimé',
    surOrdonnance: initial?.surOrdonnance ?? false,
    prixDT: initial?.prixDT ?? '',
    molecules: initial?.molecules?.map((m) => m.id) || [],
    indications: initial?.indications?.map((i) => i.id) || [],
  }));
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.molecules.length) {
      setError('Un médicament doit contenir au moins une molécule (axiome de l’ontologie).');
      return;
    }
    setSaving(true);
    setError(null);
    const body = { ...form, prixDT: Number(form.prixDT), surOrdonnance: form.surOrdonnance === true || form.surOrdonnance === 'true' };
    try {
      const res = editing ? await api.updateMedicament(initial.id, body) : await api.createMedicament(body);
      onSaved(res);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const r = ref.data;
  const formes = r ? Array.from(new Set([...r.formes, 'comprimé', 'gélule', 'sirop', 'sachet', 'injectable'])) : [];
  return (
    <Modal title={editing ? `Modifier ${initial.label}` : 'Nouveau médicament'} onClose={onClose} wide>
      {ref.loading && <Loading />}
      <ErrorBox message={ref.error} />
      {r && (
        <form className="form" onSubmit={submit}>
          <div className="form-grid">
            <Field label="Nom commercial *">
              <input className="input" required minLength={2} maxLength={80} value={form.nomCommercial} onChange={set('nomCommercial')} />
            </Field>
            <Field label="Type *" hint="La sous-classe (sur / sans ordonnance) est déduite automatiquement.">
              <select className="input" value={form.type} onChange={set('type')}>
                <option value="Princeps">Princeps (médicament d’origine)</option>
                <option value="Generique">Générique</option>
              </select>
            </Field>
            <Field label="Dosage *" hint="Ex. 500 mg">
              <input className="input" required maxLength={30} value={form.dosage} onChange={set('dosage')} />
            </Field>
            <Field label="Forme galénique *">
              <select className="input" value={form.formeGalenique} onChange={set('formeGalenique')}>
                {formes.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </Field>
            <Field label="Prix (DT) *">
              <input className="input" type="number" required min="0" step="0.1" value={form.prixDT} onChange={set('prixDT')} />
            </Field>
            <Field label="Délivrance *">
              <select className="input" value={String(form.surOrdonnance)} onChange={(e) => set('surOrdonnance')(e.target.value === 'true')}>
                <option value="false">Sans ordonnance</option>
                <option value="true">Sur ordonnance</option>
              </select>
            </Field>
          </div>
          <ChipSelect label="Molécules contenues * (contientMolecule)" options={r.molecules} value={form.molecules} onChange={set('molecules')} />
          <ChipSelect label="Indiqué pour (estIndiquePour)" options={r.pathologies} value={form.indications} onChange={set('indications')} />
          <ErrorBox message={error} />
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={saving}><Save size={16} aria-hidden="true" /> {saving ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      )}
    </Modal>
  );
}
