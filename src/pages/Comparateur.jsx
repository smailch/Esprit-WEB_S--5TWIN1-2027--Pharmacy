import { Link, useSearchParams } from 'react-router-dom';
import { Scale, TrendingDown } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, Empty, SparqlPanel, Badge, CLASS_LABELS, fmtPrix } from '../app/ui.jsx';

export default function Comparateur() {
  const [params, setParams] = useSearchParams();
  const selected = params.get('medicament') || 'Advil';
  const meds = useApi(() => api.medicaments({ tri: 'label' }), []);
  const res = useApi(() => api.alternatives(selected), [selected]);
  const d = res.data;
  const maxPrix = d ? Math.max(d.reference.prixDT || 0, ...d.alternatives.map((a) => a.prixDT || 0)) : 1;

  return (
    <>
      <PageHeader eyebrow="Valeur ajoutée" title="Comparateur princeps / générique">
        <p>Trouve les médicaments de <strong>même composition</strong> (mêmes molécules, aucune en plus) et calcule l’économie en SPARQL (BIND).</p>
      </PageHeader>

      <div className="filter-bar">
        <label className="field-inline">
          <span>Médicament de référence</span>
          <select className="input" value={selected} onChange={(e) => setParams({ medicament: e.target.value })}>
            {(meds.data || []).map((m) => <option key={m.id} value={m.id}>{m.label} — {fmtPrix(m.prixDT)}</option>)}
          </select>
        </label>
      </div>

      <ErrorBox message={res.error} />
      {res.loading && !d ? <Loading /> : d && (
        <>
          {d.meilleure ? (
            <div className="saving">
              <TrendingDown size={28} aria-hidden="true" />
              <div>
                <p className="saving-value">−{d.meilleure.economiePct} %</p>
                <p>En choisissant <strong>{d.meilleure.label}</strong> au lieu de {d.reference.label}, vous économisez {fmtPrix(d.meilleure.economie)} par boîte.</p>
              </div>
            </div>
          ) : (
            <p className="note-plain">Aucune alternative moins chère avec la même composition pour {d.reference.label}.</p>
          )}

          <section className="panel">
            <h2 className="panel-title"><Scale size={16} aria-hidden="true" /> Comparaison des prix</h2>
            <ul className="bars">
              <li className="bar-row is-ref">
                <span className="bar-label"><Link to={`/medicaments/${d.reference.id}`}>{d.reference.label}</Link> <Badge tone="dark">référence</Badge></span>
                <span className="bar"><span style={{ width: `${((d.reference.prixDT || 0) / maxPrix) * 100}%` }} /></span>
                <span className="bar-value">{fmtPrix(d.reference.prixDT)}</span>
              </li>
              {d.alternatives.map((a) => (
                <li key={a.id} className={`bar-row ${a.economie > 0 ? 'is-cheaper' : ''}`}>
                  <span className="bar-label"><Link to={`/medicaments/${a.id}`}>{a.label}</Link> <Badge tone={a.type === 'Generique' ? 'gold' : 'neutral'}>{CLASS_LABELS[a.type] || a.type}</Badge></span>
                  <span className="bar"><span style={{ width: `${((a.prixDT || 0) / maxPrix) * 100}%` }} /></span>
                  <span className="bar-value">{fmtPrix(a.prixDT)} {a.economie > 0 && <small className="gain">−{a.economiePct} %</small>}{a.economie < 0 && <small className="loss">+{Math.abs(a.economiePct)} %</small>}</span>
                </li>
              ))}
            </ul>
            {!d.alternatives.length && <Empty>Aucun autre médicament n’a exactement la même composition.</Empty>}
          </section>
        </>
      )}
      <SparqlPanel items={res.sparql.filter((s) => !s.titre.startsWith('Attributs') )} defaultOpen />
    </>
  );
}
