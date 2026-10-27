import { useEffect, useRef, useState } from 'react';
import { api } from './api';
import { storage, useApi } from './hooks';
import { Badge, ErrorBox, Loading, ResultTable } from './ui';

const HISTORY_KEY = 'ahmed.nlp.history';
const TYPE_LABEL = {
  PATHOLOGIE: 'pathologie', TYPE: 'type de pathologie', PATIENT: 'patient', MEDECIN: 'médecin', PHARMACIEN: 'pharmacien',
  MEDICAMENT: 'médicament', MOLECULE: 'molécule', SPECIALITE: 'spécialité', CLASSE: 'classe', PRESCRIPTION: 'ordonnance',
};

function Highlighted({ text, entities }) {
  const parts = [];
  let pos = 0;
  entities.forEach((e, i) => {
    if (e.start < pos) return;
    parts.push(text.slice(pos, e.start));
    parts.push(
      <mark key={i} className={`ent ent-${e.type.toLowerCase()}`}
        title={`${TYPE_LABEL[e.type] || e.type} → :${e.id} (${e.method}, ${Math.round(e.score * 100)} %)`}>
        {text.slice(e.start, e.end)}<small>{TYPE_LABEL[e.type] || e.type}</small>
      </mark>,
    );
    pos = e.end;
  });
  parts.push(text.slice(pos));
  return <p className="highlighted">{parts}</p>;
}

function Steps({ r }) {
  return (
    <details className="card steps">
      <summary>Étapes du pipeline NLP (spaCy · RapidFuzz · scikit-learn)</summary>
      <ol>
        <li><b>Normalisation</b> : <code>{r.normalisee}</code></li>
        <li>
          <b>Analyse spaCy</b> (tokens, lemmes, POS, dépendances)
          <div className="table-wrap">
            <table className="compact">
              <thead><tr><th scope="col">Token</th><th scope="col">Lemme</th><th scope="col">POS</th><th scope="col">Dépendance</th></tr></thead>
              <tbody>{r.tokens.map((t, i) => <tr key={i}><td>{t.text}</td><td>{t.lemma}</td><td>{t.pos}</td><td>{t.dep}</td></tr>)}</tbody>
            </table>
          </div>
        </li>
        <li>
          <b>Entités de l&apos;ontologie</b> (PhraseMatcher + RapidFuzz) :{' '}
          {r.entites.length ? r.entites.map((e) => (
            <Badge key={e.start} tone={e.method === 'exact' ? 'green' : 'gold'}>{e.text} → :{e.id} ({e.method})</Badge>
          )) : 'aucune'}
        </li>
        <li><b>Contraintes</b> : <code>{JSON.stringify(r.contraintes)}</code></li>
        <li>
          <b>Intention</b> sur la question masquée <code>{r.masquee}</code> — {r.methode}
          <ul>{r.classement.map((c) => <li key={c.intention}>{c.intention} : {Math.round(c.proba * 100)} %</li>)}</ul>
        </li>
        <li><b>Génération SPARQL</b> par gabarit paramétré (aucun LLM), puis exécution sur le triplestore.</li>
      </ol>
    </details>
  );
}

export default function AssistantSante({ initial }) {
  const [question, setQuestion] = useState(initial || '');
  const [result, setResult] = useState(null);
  const [state, setState] = useState({ loading: false, error: null });
  const [history, setHistory] = useState(() => storage.get(HISTORY_KEY, []));
  const [copied, setCopied] = useState(false);
  const examples = useApi((signal) => api.exemples({ signal }), []);
  const ctrl = useRef(null);

  const ask = async (q) => {
    const text = (q ?? question).trim();
    if (!text) return;
    setQuestion(text);
    ctrl.current?.abort();
    ctrl.current = new AbortController();
    setState({ loading: true, error: null });
    try {
      const r = await api.ask(text, { signal: ctrl.current.signal });
      setResult(r);
      setState({ loading: false, error: null });
      const h = [text, ...history.filter((x) => x !== text)].slice(0, 10);
      setHistory(h);
      storage.set(HISTORY_KEY, h);
    } catch (err) {
      if (err.name !== 'AbortError') setState({ loading: false, error: err });
    }
  };

  useEffect(() => {
    if (initial) ask(initial);
    return () => ctrl.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result.sparql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const suggestionsList = [...(examples.data || []), ...history];

  return (
    <>
      <h1>Assistant NLP</h1>
      <p className="lead muted">Posez une question en français : elle est traduite en requête SPARQL puis exécutée.
        Outils : <b>spaCy</b>, <b>RapidFuzz</b>, <b>scikit-learn</b> — aucune API de LLM.</p>
      <form className="ask" onSubmit={(e) => { e.preventDefault(); ask(); }}>
        <label className="sr-only" htmlFor="question">Votre question</label>
        <input id="question" list="question-list" value={question} onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ex. Quels patients souffrent de diabète ?" autoComplete="off" />
        <datalist id="question-list">{suggestionsList.map((q) => <option key={q} value={q} />)}</datalist>
        <button className="btn primary" disabled={state.loading}>{state.loading ? 'Analyse…' : 'Demander'}</button>
      </form>
      <div className="chips-row">
        <span className="muted small">Exemples :</span>
        {examples.data?.map((q) => <button key={q} className="chip" onClick={() => ask(q)}>{q}</button>)}
      </div>
      {history.length > 0 && (
        <div className="chips-row">
          <span className="muted small">Historique :</span>
          {history.map((q) => <button key={q} className="chip outline" onClick={() => ask(q)}>{q}</button>)}
          <button className="link-btn small" onClick={() => { setHistory([]); storage.set(HISTORY_KEY, []); }}>effacer</button>
        </div>
      )}

      {state.loading && <Loading label="Analyse de la question (le premier appel charge spaCy, ~4 s)…" />}
      <ErrorBox error={state.error} />

      {result && !state.loading && (
        <section className="mt" aria-live="polite">
          <div className={`card answer ${result.compris ? '' : 'warn'}`}>
            <Highlighted text={result.question} entities={result.entites} />
            <p className="answer-msg">{result.message}</p>
            <div className="meta">
              <Badge tone="green">intention : {result.intention}</Badge>
              <span className="confidence" title="Confiance">
                <span className="bar"><span style={{ width: `${result.confiance * 100}%` }} /></span>
                {Math.round(result.confiance * 100)} %
              </span>
            </div>
            {result.suggestions.length > 0 && (
              <div className="chips-row">
                <span className="muted small">Essayez plutôt :</span>
                {result.suggestions.map((q) => <button key={q} className="chip" onClick={() => ask(q)}>{q}</button>)}
              </div>
            )}
          </div>

          {result.sparql && (
            <div className="card mt">
              <div className="page-head">
                <h2>Requête SPARQL générée</h2>
                <button className="btn small" onClick={copy}>{copied ? 'Copié ✓' : 'Copier'}</button>
              </div>
              <pre className="code">{result.sparql}</pre>
            </div>
          )}

          {result.resultat?.kind === 'SELECT' && (
            <div className="card mt">
              <h2>Résultats</h2>
              <ResultTable vars={result.resultat.vars} rows={result.resultat.rows} name="reponse-nlp" />
            </div>
          )}
          {result.resultat?.kind === 'ASK' && (
            <div className="card mt"><h2>Réponse ASK</h2><p className="big">{result.resultat.boolean ? 'Oui ✓' : 'Non ✗'}</p></div>
          )}
          <Steps r={result} />
        </section>
      )}
    </>
  );
}
