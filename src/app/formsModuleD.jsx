import { useState } from 'react';
import { Save } from 'lucide-react';
import { apiD } from '../api/moduleD.js';
import { useApi } from './useApi.js';
import { ChipSelect, ErrorBox, Loading, Modal } from './ui.jsx';

function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

const today = () => new Date().toISOString().slice(0, 10);

/* =========================== Prescription =========================== */
export function PrescriptionForm({ initial, onClose, onSaved }) {
  const ref = useApi(() => apiD.referentiels(), []);
  const editing = Boolean(initial);
  const [form, setForm] = useState(() => ({
    type: initial?.type || 'PrescriptionNormale',
    datePrescription: initial?.datePrescription || today(),
    dureeJours: initial?.dureeJours ?? 7,
    posologie: initial?.posologie || '',
    medecin: initial?.medecin?.id || '',
    patient: initial?.patient?.id || '',
    pharmacien: initial?.pharmacien?.id || '',
    medicaments: initial?.medicaments?.map((m) => m.id) || [],
    libelle: initial?.label || '',
  }));
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));

  const r = ref.data;
  const typeInfo = r?.typesPrescription.find((t) => t.id === form.type);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.medicaments.length) {
      setError('Une prescription contient au moins un médicament (restriction OWL de la classe Prescription).');
      return;
    }
    setSaving(true);
    setError(null);
    const body = {
      ...form,
      dureeJours: Number(form.dureeJours),
      pharmacien: form.pharmacien || null,
      libelle: form.libelle.trim() || null,
    };
    try {
      const res = editing ? await apiD.updatePrescription(initial.id, body) : await apiD.createPrescription(body);
      onSaved(res);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <Modal title={editing ? `Modifier ${initial.label}` : 'Nouvelle prescription'} onClose={onClose} wide>
      {ref.loading && <Loading />}
      <ErrorBox message={ref.error} />
      {r && (
        <form className="form" onSubmit={submit}>
          <div className="form-grid">
            <Field label="Type *" hint={typeInfo ? `estRenouvelable = ${typeInfo.renouvelable} (déduit du type)` : null}>
              <select className="input" value={form.type} onChange={set('type')}>
                {r.typesPrescription.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </Field>
            <Field label="Date de prescription *" hint="xsd:date — au plus tard aujourd’hui">
              <input className="input" type="date" required max={today()} min="2000-01-01" value={form.datePrescription} onChange={set('datePrescription')} />
            </Field>
            <Field label="Patient * (concernePatient)">
              <select className="input" required value={form.patient} onChange={set('patient')}>
                <option value="">Choisir…</option>
                {r.patients.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </Field>
            <Field label="Médecin * (prescritPar)">
              <select className="input" required value={form.medecin} onChange={set('medecin')}>
                <option value="">Choisir…</option>
                {r.medecins.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </Field>
            <Field label="Durée (jours) *" hint="Renouvellement court ≤ 90 j · long > 90 j">
              <input className="input" type="number" required min="1" max="3650" value={form.dureeJours} onChange={set('dureeJours')} />
            </Field>
            <Field label="Délivrée par (estDelivreePar)">
              <select className="input" value={form.pharmacien} onChange={set('pharmacien')}>
                <option value="">Pas encore délivrée</option>
                {r.pharmaciens.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </Field>
            <Field label="Posologie *">
              <input className="input" required minLength={2} maxLength={200} value={form.posologie} onChange={set('posologie')} placeholder="Ex. 1 comprimé matin et soir" />
            </Field>
            <Field label="Libellé" hint={editing ? 'Laisser vide pour conserver le libellé actuel' : 'Par défaut « Ordonnance NNN »'}>
              <input className="input" maxLength={120} value={form.libelle} onChange={set('libelle')} />
            </Field>
          </div>
          <ChipSelect label="Médicaments prescrits * (prescritMedicament)" options={r.medicaments} value={form.medicaments} onChange={set('medicaments')} max={10} />
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

/* =========================== Donnée clinique =========================== */
const EXAMENS = ['SigneVital', 'AnalyseBiologique'];

export function DonneeForm({ initial, onClose, onSaved }) {
  const ref = useApi(() => apiD.referentiels(), []);
  const editing = Boolean(initial);
  const [form, setForm] = useState(() => ({
    type: initial?.type || 'AnalyseBiologique',
    patient: initial?.patient?.id || '',
    libelle: initial?.label || '',
    dateMesure: initial?.dateMesure || today(),
    valeur: initial?.valeur ?? '',
    unite: initial?.unite || '',
    molecule: initial?.molecule?.id || '',
    pathologie: initial?.pathologie?.id || '',
  }));
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));
  const examen = EXAMENS.includes(form.type);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const body = {
      type: form.type, patient: form.patient, libelle: form.libelle.trim(), dateMesure: form.dateMesure,
      valeur: examen ? Number(form.valeur) : null, unite: examen ? form.unite.trim() : null,
      molecule: form.type === 'Allergie' ? form.molecule : null,
      pathologie: form.type === 'Antecedent' ? form.pathologie : null,
    };
    try {
      const res = editing ? await apiD.updateDonnee(initial.id, body) : await apiD.createDonnee(body);
      onSaved(res);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const r = ref.data;
  const feuilles = r ? r.typesDonnee.filter((t) => !['ExamenClinique', 'HistoriqueMedical'].includes(t.id)) : [];
  return (
    <Modal title={editing ? `Modifier ${initial.label}` : 'Nouvelle donnée clinique'} onClose={onClose} wide>
      {ref.loading && <Loading />}
      <ErrorBox message={ref.error} />
      {r && (
        <form className="form" onSubmit={submit}>
          <div className="form-grid">
            <Field label="Type *" hint={examen ? 'Examen clinique : valeur + unité (domaine de :valeur / :unite)' : 'Historique médical'}>
              <select className="input" value={form.type} onChange={set('type')}>
                {feuilles.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </Field>
            <Field label="Patient * (estDonneeDe)" hint={editing ? 'L’identifiant (URI) ne change pas.' : 'L’URI suit la convention Mesure_Patient (ex. Glycemie_Ali)'}>
              <select className="input" required value={form.patient} onChange={set('patient')}>
                <option value="">Choisir…</option>
                {r.patients.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </Field>
            <Field label="Libellé * (rdfs:label)">
              <input className="input" required minLength={2} maxLength={120} value={form.libelle} onChange={set('libelle')}
                placeholder={examen ? 'Ex. Glycémie à jeun' : form.type === 'Allergie' ? 'Ex. Allergie à l’amoxicilline' : 'Ex. Antécédent d’ulcère'} />
            </Field>
            <Field label="Date * (dateMesure, xsd:date)">
              <input className="input" type="date" required max={today()} min="1900-01-01" value={form.dateMesure} onChange={set('dateMesure')} />
            </Field>
            {examen && (
              <>
                <Field label="Valeur * (xsd:decimal)">
                  <input className="input" type="number" required step="any" value={form.valeur} onChange={set('valeur')} />
                </Field>
                <Field label="Unité *">
                  <input className="input" required maxLength={20} value={form.unite} onChange={set('unite')} placeholder="g/L, mmHg, °C, mL/min…" />
                </Field>
              </>
            )}
            {form.type === 'Allergie' && (
              <Field label="Molécule * (allergiqueA)" hint="Prise en compte immédiatement par les alertes de prescription">
                <select className="input" required value={form.molecule} onChange={set('molecule')}>
                  <option value="">Choisir…</option>
                  {r.molecules.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                </select>
              </Field>
            )}
            {form.type === 'Antecedent' && (
              <Field label="Pathologie * (porteSur)" hint="Comparée aux contre-indications des médicaments prescrits">
                <select className="input" required value={form.pathologie} onChange={set('pathologie')}>
                  <option value="">Choisir…</option>
                  {r.pathologies.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                </select>
              </Field>
            )}
          </div>
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
