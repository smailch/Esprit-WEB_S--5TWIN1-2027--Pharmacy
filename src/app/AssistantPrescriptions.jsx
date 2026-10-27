import { useEffect, useRef, useState } from 'react';
import { Send, Sparkles, History, Cpu, Trash2, Wand2, HelpCircle } from 'lucide-react';
import { apiD } from '../api/moduleD.js';
import { useApi } from './useApi.js';
import { Loading, ErrorBox, ResultTable, CodeBlock, Badge } from './ui.jsx';

const HISTORY_KEY = 'prescrinlu-historique';
const METHODS = { dictionnaire: 'dictionnaire', regle: 'règle', approximatif: 'faute corrigée' };

function readHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch {
    return [];
  }
}

function writeHistory(items) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 15)));
  } catch { /* stockage indisponible : l'historique reste en mémoire */ }
}

function Confidence({ value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <span className="confidence" title="Probabilité (softmax des scores des règles)">
      <span className="confidence-bar"><span style={{ width: `${pct}%` }} /></span>
      {pct} %
    </span>
  );
}

function ModelCard() {
  const res = useApi(() => apiD.modele(), []);
  const m = res.data;
  if (res.loading) return <Loading label="Évaluation du modèle sur le jeu de questions annotées…" />;
  if (res.error || !m) return <ErrorBox message={res.error} />;
  const ev = m.evaluation;
  return (
    <div className="model-card">
      <dl className="model-facts">
        <div><dt>Nom</dt><dd>{m.nom}</dd></div>
        <div><dt>Type</dt><dd>{m.type}</dd></div>
        <div><dt>Mode spaCy</dt><dd>{m.mode}</dd></div>
        <div><dt>Évaluation</dt><dd><strong>{Math.round(ev.precisionIntention * 100)} %</strong> d’intentions correctes et {Math.round(ev.precisionEntites * 100)} % d’entités sur {ev.questions} questions annotées</dd></div>
        <div><dt>LLM</dt><dd>{m.llm}</dd></div>
      </dl>
      <p className="panel-title">Bibliothèques utilisées</p>
      <ul className="lib-list">{m.bibliotheques.map((b) => <li key={b.nom}><strong>{b.nom} {b.version}</strong> — {b.role}</li>)}</ul>
      <p className="panel-title">Pipeline</p>
      <ol className="pipeline">{m.pipeline.map((p) => <li key={p}>{p}</li>)}</ol>
      <p className="panel-title">Intentions reconnues ({m.intentions.length})</p>
      <ul className="lib-list small">{m.intentions.map((i) => <li key={i.nom}><span className="mono">{i.nom}</span> — {i.label} <span className="muted">« {i.exemple} »</span></li>)}</ul>
      {ev.erreurs.length > 0 && (
        <>
          <p className="panel-title">Erreurs restantes</p>
          <ul className="lib-list small">{ev.erreurs.map((e) => <li key={e.question}>« {e.question} » : attendu {e.attendu}, obtenu {e.obtenu}</li>)}</ul>
        </>
      )}
    </div>
  );
}

function Results({ a }) {
  if (a.resultType === 'ask') return <p className={`verdict ${a.answer ? 'is-ok' : 'is-ko'}`}>Réponse ASK : <strong>{a.answer ? 'VRAI' : 'FAUX'}</strong></p>;
  if (!a.results.length) return null;
  const cols = Object.keys(a.results[0]);
  return <ResultTable columns={cols} rows={a.results} filename="reponse-prescrinlu.csv" linkTypes={{ medicament: 'Medicament', molecule: 'Molecule', mol: 'Molecule', med: 'Medicament' }} />;
}

export default function AssistantPrescriptions() {
  const sugg = useApi(() => apiD.suggestions(), []);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState(readHistory);
  const [showModel, setShowModel] = useState(false);
  const inputRef = useRef(null);

  // « ?q=… » pose directement une question (liens de démonstration).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) ask(q);
    else inputRef.current?.focus();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const ask = async (q) => {
    const text = (q ?? question).trim();
    if (text.length < 3) return;
    setQuestion(text);
    setLoading(true);
    setError(null);
    try {
      setAnswer(await apiD.ask(text));
      const next = [text, ...history.filter((h) => h !== text)];
      setHistory(next);
      writeHistory(next);
    } catch (e) {
      setError(e.message);
      setAnswer(null);
    } finally {
      setLoading(false);
    }
  };

  const a = answer;
  return (
    <>
      <div className="assistant-intro">
        <p>Le modèle local <strong>PrescriNLU-D</strong> (spaCy + PhraseMatcher + RapidFuzz + règles pondérées) traduit votre question sur les <strong>prescriptions et les données cliniques</strong> en requête SPARQL, l’exécute avec RDFLib et explique chaque étape. Aucune API de LLM n’est utilisée.</p>
        <button type="button" className="btn btn-ghost" aria-expanded={showModel} onClick={() => setShowModel((v) => !v)}><Cpu size={16} aria-hidden="true" /> À propos du modèle</button>
      </div>

      {showModel && <section className="panel"><ModelCard /></section>}

      <form className="ask" onSubmit={(e) => { e.preventDefault(); ask(); }}>
        <label htmlFor="question-d" className="sr-only">Votre question sur les prescriptions</label>
        <input id="question-d" ref={inputRef} className="ask-input" placeholder="Ex. : le patient Youssef a-t-il une prescription contre-indiquée ?" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={300} autoComplete="off" />
        <button type="submit" className="btn btn-primary" disabled={loading || question.trim().length < 3}><Send size={16} aria-hidden="true" /> Demander</button>
      </form>

      <div className="suggestions" aria-label="Exemples de questions">
        <Wand2 size={15} aria-hidden="true" />
        {(sugg.data || []).map((s) => <button key={s} type="button" className="chip" onClick={() => ask(s)}>{s}</button>)}
      </div>

      <ErrorBox message={error} />
      {loading && <Loading label="Analyse de la question…" />}

      {a && !loading && (
        <div className="answer-layout">
          <section className="panel answer">
            <p className={`answer-text ${a.compris ? '' : 'is-unknown'}`}>
              {!a.compris && <HelpCircle size={20} aria-hidden="true" />} {a.message}
            </p>
            {a.compris && <p className="muted small">{a.count} résultat{a.count > 1 ? 's' : ''} · {a.dureeMs} ms</p>}
            <Results a={a} />
          </section>

          <aside className="panel analysis">
            <p className="panel-title"><Sparkles size={15} aria-hidden="true" /> Comment la question a été comprise</p>
            <dl className="model-facts">
              <div>
                <dt>Intention</dt>
                <dd>{a.intent ? <><Badge tone="dark">{a.intent}</Badge> <Confidence value={a.confidence} /></> : <Badge tone="danger">non comprise</Badge>}</dd>
                {a.intentLabel && <dd className="small muted">{a.intentLabel}</dd>}
              </div>
              {a.indices.length > 0 && <div><dt>Indices déclenchés</dt><dd className="small">{a.indices.join(' · ')}</dd></div>}
              {a.alternatives?.length > 0 && (
                <div><dt>Autres hypothèses</dt><dd className="small">{a.alternatives.map((x) => `${x.intention} (${x.proba != null ? `${Math.round(x.proba * 100)} %` : `score ${x.score}`})`).join(' · ')}</dd></div>
              )}
              <div>
                <dt>Entités reconnues</dt>
                <dd>
                  {a.entities.length ? (
                    <ul className="entity-list">
                      {a.entities.map((e) => (
                        <li key={e.type + e.id}>
                          <span className="mono">« {e.texte} »</span> → <strong>{e.type === 'FORME' ? e.label : `:${e.id}`}</strong> <span className="muted small">({e.type}, {METHODS[e.methode]})</span>
                          {e.methode === 'approximatif' && <Badge tone="gold" title="Similarité RapidFuzz">{e.score} %</Badge>}
                        </li>
                      ))}
                    </ul>
                  ) : <span className="muted">aucune</span>}
                </dd>
              </div>
              {a.periode && <div><dt>Période</dt><dd className="mono small">« {a.periode.texte} » → {a.periode.debut || '…'} / {a.periode.fin || '…'}</dd></div>}
              {a.entitesInconnues.length > 0 && <div><dt>Entités inconnues</dt><dd>{a.entitesInconnues.map((u) => <Badge key={u} tone="danger">{u}</Badge>)}</dd></div>}
              {a.pretraitement.corrections.length > 0 && (
                <div><dt>Mots corrigés</dt><dd className="small">{a.pretraitement.corrections.map((c) => `${c.mot} → ${c.correction} (${c.score} %)`).join(' · ')}</dd></div>
              )}
              <div><dt>Lemmes (spaCy)</dt><dd className="mono small">{a.pretraitement.lemmes}</dd></div>
            </dl>
            <ol className="pipeline small">{a.etapes.map((s) => <li key={s.nom}><strong>{s.nom}</strong> — {s.ms} ms</li>)}</ol>
            <p className="muted small">{a.mode}</p>
          </aside>

          {a.sparql && (
            <section className="panel answer-sparql">
              <p className="panel-title">Requête SPARQL générée ({a.resultType?.toUpperCase()})</p>
              {a.explication.length > 0 && <ul className="explain">{a.explication.map((x) => <li key={x}>{x}</li>)}</ul>}
              <CodeBlock code={a.sparql} />
            </section>
          )}
          {!a.sparql && a.explication.length > 0 && (
            <section className="panel answer-sparql"><ul className="explain">{a.explication.map((x) => <li key={x}>{x}</li>)}</ul></section>
          )}
        </div>
      )}

      {history.length > 0 && (
        <section className="history">
          <p className="panel-title"><History size={15} aria-hidden="true" /> Historique</p>
          <div className="chips">
            {history.map((h) => <button key={h} type="button" className="chip" onClick={() => ask(h)}>{h}</button>)}
            <button type="button" className="btn-link" onClick={() => { setHistory([]); writeHistory([]); }}><Trash2 size={13} aria-hidden="true" /> Effacer</button>
          </div>
        </section>
      )}
    </>
  );
}
