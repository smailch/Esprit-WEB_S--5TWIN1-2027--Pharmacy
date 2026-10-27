import { useState } from 'react';
import { ShieldAlert, ShieldCheck, Copy } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, SparqlPanel, ChipSelect } from '../app/ui.jsx';

export default function Interactions() {
  const meds = useApi(() => api.medicaments({ tri: 'label' }), []);
  const [selected, setSelected] = useState(['Advil', 'Aspegic']);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const verify = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.interactions(selected));
    } catch (e) {
      setError(e.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const options = (meds.data || []).map((m) => ({ id: m.id, label: m.label }));
  const d = result?.data;
  return (
    <>
      <PageHeader eyebrow="Valeur ajoutée" title="Vérificateur d’interactions">
        <p>
          Sélectionnez de 2 à 10 médicaments. Le système détecte les <strong>interactions entre molécules</strong> (propriété
          symétrique <code>interagitAvec</code> : déclarée dans un seul sens, déduite dans l’autre) et les <strong>doublons de
          principe actif</strong> (risque de surdosage).
        </p>
      </PageHeader>

      <section className="panel">
        {meds.loading && !meds.data ? <Loading /> : (
          <ChipSelect label="Médicaments à associer" options={options} value={selected} onChange={(v) => { setSelected(v); setResult(null); }} max={10} />
        )}
        <div className="form-actions">
          <button type="button" className="btn btn-primary" disabled={selected.length < 2 || loading} onClick={verify}>
            <ShieldAlert size={16} aria-hidden="true" /> {loading ? 'Vérification…' : 'Vérifier l’association'}
          </button>
        </div>
      </section>

      <ErrorBox message={error} />
      {d && (
        d.sur ? (
          <div className="verdict is-ok" role="status"><ShieldCheck size={26} aria-hidden="true" /><p>Aucune interaction ni doublon détecté dans l’ontologie pour cette association.</p></div>
        ) : (
          <ul className="alerts" role="status">
            {d.alertes.map((a, i) => (
              <li key={i} className={`alert alert-${a.niveau}`}>
                {a.niveau === 'doublon' ? <Copy size={20} aria-hidden="true" /> : <ShieldAlert size={20} aria-hidden="true" />}
                <div>
                  <p className="alert-kind">{a.niveau === 'doublon' ? 'Doublon de principe actif' : 'Interaction médicamenteuse'}</p>
                  <p>{a.message}</p>
                </div>
              </li>
            ))}
          </ul>
        )
      )}
      <p className="disclaimer">Outil pédagogique fondé sur les données fictives de l’ontologie : il ne remplace pas l’avis d’un professionnel de santé.</p>
      {result && <SparqlPanel items={result.sparql} defaultOpen />}
    </>
  );
}
