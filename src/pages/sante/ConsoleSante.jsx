// Console SPARQL du module Pathologie + Personne — même présentation que les consoles des modules A et D.
import { useState } from 'react';
import { Play, ShieldCheck } from 'lucide-react';
import { api } from './api';
import { useApi } from '../../app/useApi.js';
import { PageHeader, Loading, ErrorBox, ResultTable, CodeBlock, Badge } from '../../app/ui.jsx';

const DEFAULT = `SELECT ?patient ?age ?pathologie WHERE {
  ?p a/rdfs:subClassOf* :Patient ; rdfs:label ?patient ; :age ?age ;
     :souffreDe ?m .
  ?m a/rdfs:subClassOf* :MaladieChronique ; rdfs:label ?pathologie .
} ORDER BY ?patient`;

function Result({ data }) {
  if (!data) return null;
  if (data.type === 'ask') return <p className={`verdict ${data.resultat ? 'is-ok' : 'is-ko'}`}>Réponse ASK : <strong>{data.resultat ? 'VRAI' : 'FAUX'}</strong></p>;
  if (data.type === 'graphe') return <><p className="muted small">{data.triplets} triplets construits (CONSTRUCT)</p><CodeBlock code={data.turtle} /></>;
  return (
    <>
      {data.tronque && <p className="muted small">Résultat tronqué à {data.lignes.length} lignes.</p>}
      <ResultTable columns={data.colonnes} rows={data.lignes} filename="requete-sante.csv" />
    </>
  );
}

export default function ConsoleSante() {
  const cat = useApi(() => api.requetes(), []);
  const [active, setActive] = useState(null);
  const [text, setText] = useState(DEFAULT);
  const [out, setOut] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);

  const run = async (fn) => {
    setRunning(true);
    setError(null);
    try {
      setOut((await fn()).data);
    } catch (e) {
      setError(e.message);
      setOut(null);
    } finally {
      setRunning(false);
    }
  };

  const pick = (q) => {
    setActive(q.nom);
    setText(q.requete);
    if (q.lectureSeule) run(() => api.executerRequete(q.nom));
    else { setOut(null); setError(null); }
  };

  const current = cat.data?.find((q) => q.nom === active);
  return (
    <>
      <PageHeader eyebrow="Pathologie + Personne · Requêtes SPARQL" title="Console SPARQL — Pathologie + Personne">
        <p>Catalogue des {cat.data?.length || 36} requêtes nommées du module (CRUD, filtres, recherche, hiérarchie, agrégats,
          chemins, alertes, ASK). La requête libre passe par <code>/api/sante/sparql</code> : elle est <strong>analysée</strong>{' '}
          (parseur rdflib + inspection de l’algèbre) et seules SELECT, ASK et CONSTRUCT sont exécutées ; INSERT, DELETE, DROP,
          SERVICE et FROM sont refusés. Les préfixes <code>:</code>, <code>rdf:</code>, <code>rdfs:</code>, <code>owl:</code>,{' '}
          <code>xsd:</code> sont ajoutés automatiquement.</p>
      </PageHeader>

      <div className="split">
        <aside className="panel catalogue" aria-label="Catalogue de requêtes du module Pathologie + Personne">
          <p className="panel-title">Catalogue</p>
          {cat.loading && <Loading />}
          <ErrorBox message={cat.error} />
          <ul>
            {(cat.data || []).map((q) => (
              <li key={q.nom}>
                <button type="button" className={`cat-item ${active === q.nom ? 'is-active' : ''}`} onClick={() => pick(q)} aria-pressed={active === q.nom}>
                  <span className="cat-name">{q.nom.split('_')[0]} · {q.titre}</span>
                  <span className="cat-notion">{q.notion}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="console">
          {current && <p className="console-notion"><Badge tone="gold">{current.nom.split('_')[0]}</Badge> {current.notion}</p>}
          <label className="sr-only" htmlFor="sparql-sante-editor">Requête SPARQL</label>
          <textarea id="sparql-sante-editor" className="editor" spellCheck={false} value={text}
            onChange={(e) => { setText(e.target.value); setActive(null); }} rows={12} />
          <div className="form-actions">
            {current && !current.lectureSeule && <span className="muted small">Exemple de mise à jour : exécuté uniquement via les formulaires.</span>}
            <span className="muted small"><ShieldCheck size={13} aria-hidden="true" /> lecture seule contrôlée</span>
            <button type="button" className="btn btn-primary" disabled={running} onClick={() => run(() => api.sparql(text))}>
              <Play size={16} aria-hidden="true" /> {running ? 'Exécution…' : 'Exécuter'}
            </button>
          </div>
          <ErrorBox message={error} />
          {running ? <Loading label="Exécution de la requête…" /> : <Result data={out} />}
        </section>
      </div>
    </>
  );
}
