import { useState } from 'react';
import { api } from '../api/client';
import { download } from '../hooks';
import { ErrorBox, Loading, ResultTable } from '../components/ui';

const P = `PREFIX :     <http://example.org/pharma#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
`;

const EXAMPLES = {
  'Patients atteints d’une maladie chronique (hiérarchie)': `${P}
SELECT DISTINCT ?patient ?pathologie WHERE {
  ?p :souffreDe ?m ; rdfs:label ?patient .
  ?m a/rdfs:subClassOf* :MaladieChronique ; rdfs:label ?pathologie .
} ORDER BY ?patient`,
  'Patients par tranche d’âge (agrégat)': `${P}
SELECT ?tranche (COUNT(?p) AS ?nb) WHERE {
  ?p a/rdfs:subClassOf* :Patient ; :age ?a .
  BIND(IF(?a < 18, "enfant", IF(?a < 65, "adulte", "senior")) AS ?tranche)
} GROUP BY ?tranche`,
  'Chemin patient → contre-indication (property path)': `${P}
SELECT ?patient ?medicament ?pathologie WHERE {
  ?pat ^:concernePatient/:prescritMedicament ?med .
  ?med :contientMolecule/:aContreIndication/:concernePathologie ?patho .
  ?pat rdfs:label ?patient . ?med rdfs:label ?medicament . ?patho rdfs:label ?pathologie .
}`,
  'Sara est-elle un enfant ? (ASK)': `${P}
ASK { :Patient_Sara :age ?a . FILTER(?a < 18) }`,
  'Fiche RDF de Lina (CONSTRUCT)': `${P}
CONSTRUCT { :Patient_Lina ?p ?o } WHERE { :Patient_Lina ?p ?o }`,
};

export default function Console() {
  const [query, setQuery] = useState(Object.values(EXAMPLES)[0]);
  const [state, setState] = useState({ loading: false, error: null, data: null });

  const run = async (e) => {
    e?.preventDefault();
    setState({ loading: true, error: null, data: null });
    try {
      setState({ loading: false, error: null, data: await api.sparql(query) });
    } catch (err) {
      setState({ loading: false, error: err, data: null });
    }
  };
  const d = state.data;

  return (
    <>
      <h1>Console SPARQL</h1>
      <p className="lead muted">Lecture seule : SELECT, ASK, CONSTRUCT et DESCRIBE. Toute requête de mise à jour est refusée par le serveur.</p>
      <form onSubmit={run} className="form">
        <label className="field">
          <span>Exemples</span>
          <select onChange={(e) => setQuery(EXAMPLES[e.target.value])}>
            {Object.keys(EXAMPLES).map((k) => <option key={k}>{k}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Requête</span>
          <textarea className="code" rows={10} value={query} spellCheck={false} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => (e.ctrlKey || e.metaKey) && e.key === 'Enter' && run(e)} />
        </label>
        <div className="actions"><button className="btn primary" disabled={state.loading}>Exécuter (Ctrl+Entrée)</button></div>
      </form>
      {state.loading && <Loading />}
      <ErrorBox error={state.error} />
      {d?.kind === 'SELECT' && <section className="card mt"><ResultTable vars={d.vars} rows={d.rows} name="console" /></section>}
      {d?.kind === 'ASK' && <section className="card mt"><p className="big">{d.boolean ? 'true ✓' : 'false ✗'}</p></section>}
      {d?.turtle !== undefined && (
        <section className="card mt">
          <div className="toolbar end"><button className="btn small" onClick={() => download('resultat.ttl', d.turtle, 'text/turtle')}>Export Turtle</button></div>
          <pre className="code">{d.turtle}</pre>
        </section>
      )}
    </>
  );
}
