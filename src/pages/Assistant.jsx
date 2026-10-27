import { useEffect, useRef, useState } from 'react';
import { Send, Sparkles, History, Cpu, Trash2, Wand2 } from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from '../app/useApi.js';
import { PageHeader, Loading, ErrorBox, ResultTable, CodeBlock, Badge } from '../app/ui.jsx';

const HISTORY_KEY = 'pharmanlu-historique';

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
    <span className="confidence" title="Probabilité donnée par le classifieur">
      <span className="confidence-bar"><span style={{ width: `${pct}%` }} /></span>
      {pct} %
    </span>
  );
}

function ModelCard() {
  const res = useApi(() => api.modele(), []);
  const m = res.data;
  if (res.loading) return <Loading />;
  if (res.error || !m) return <ErrorBox message={res.error} />;
  return (
    <div className="model-card">
      <dl className="model-facts">
        <div><dt>Nom</dt><dd>{m.nom}</dd></div>
        <div><dt>Type</dt><dd>{m.type}</dd></div>
        <div><dt>Précision (test)</dt><dd><strong>{Math.round(m.metriques.precision_test * 100)} %</strong> sur {m.donnees.test} questions jamais vues</dd></div>
        <div><dt>Entraînement</dt><dd>{m.donnees.entrainement} questions · {m.intentions.length} intentions · {m.date_entrainement}</dd></div>
      </dl>
      <p className="panel-title">Bibliothèques utilisées (aucune API de LLM)</p>
      <ul className="lib-list">
        {m.bibliotheques.map((b) => <li key={b.nom}><strong>{b.nom} {b.version}</strong> — {b.role}</li>)}
      </ul>
      <p className="panel-title">Pipeline</p>
      <ol className="pipeline">{m.pipeline.map((p) => <li key={p}>{p}</li>)}</ol>
      <p className="panel-title">F1-score par intention (jeu de test)</p>
      <ul className="bars compact">
        {Object.entries(m.metriques.f1_par_intention).map(([k, v]) => (
          <li key={k} className="bar-row">
            <span className="bar-label mono small">{k}</span>
            <span className="bar"><span style={{ width: `${v * 100}%` }} /></span>
            <span className="bar-value">{Math.round(v * 100)} %</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Assistant() {
  const sugg = useApi(() => api.suggestions(), []);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState(readHistory);
  const [showModel, setShowModel] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const ask = async (q) => {
    const text = (q ?? question).trim();
    if (!text) return;
    setQuestion(text);
    setLoading(true);
    setError(null);
    try {
      const res = await api.ask(text);
      setAnswer(res.data);
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
      <PageHeader
        eyebrow="API IA · PharmaNLU-A"
        title="Assistant en langage naturel"
        actions={<button type="button" className="btn btn-ghost" aria-expanded={showModel} onClick={() => setShowModel((v) => !v)}><Cpu size={16} aria-hidden="true" /> À propos du modèle</button>}
      >
        <p>Posez une question en français : le modèle local <strong>PharmaNLU-A</strong> (spaCy + scikit-learn + RapidFuzz) la traduit en requête SPARQL, l’exécute et répond. Les fautes de frappe sont tolérées.</p>
      </PageHeader>

      {showModel && <section className="panel"><ModelCard /></section>}

      <form className="ask" onSubmit={(e) => { e.preventDefault(); ask(); }}>
        <label htmlFor="question" className="sr-only">Votre question</label>
        <input id="question" ref={inputRef} className="ask-input" placeholder="Ex. : quels médicaments contiennent de l’ibuprophène ?" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={300} autoComplete="off" />
        <button type="submit" className="btn btn-primary" disabled={loading || !question.trim()}><Send size={16} aria-hidden="true" /> Demander</button>
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
            <p className="answer-text">{a.reponse}</p>
            {a.resultats && a.resultats.type === 'ask' && <p className={`verdict ${a.resultats.resultat ? 'is-ok' : 'is-ko'}`}>{a.resultats.resultat ? 'Oui' : 'Non'}</p>}
            {a.resultats && a.resultats.type === 'select' && <ResultTable columns={a.resultats.colonnes} rows={a.resultats.lignes} filename="reponse-assistant.csv" />}
          </section>

          <aside className="panel analysis">
            <p className="panel-title"><Sparkles size={15} aria-hidden="true" /> Comment la question a été comprise</p>
            <dl className="model-facts">
              <div><dt>Intention</dt><dd>{a.compris ? <Badge tone="dark">{a.intentionLabel}</Badge> : <Badge tone="danger">non comprise</Badge>} <Confidence value={a.confiance} /></dd></div>
              {a.alternatives?.length > 0 && (
                <div><dt>Autres hypothèses</dt><dd className="small">{a.alternatives.map((x) => `${x.intention} (${Math.round(x.proba * 100)} %)`).join(' · ')}</dd></div>
              )}
              <div>
                <dt>Entités reconnues</dt>
                <dd>
                  {a.entites.length ? (
                    <ul className="entity-list">
                      {a.entites.map((e, i) => (
                        <li key={i}>
                          <span className="mono">« {e.texte} »</span> → <strong>{e.label}</strong> <span className="muted small">({e.type})</span>
                          {e.corrige && <Badge tone="gold" title={`Similarité RapidFuzz : ${e.score}`}>corrigé {e.score} %</Badge>}
                        </li>
                      ))}
                    </ul>
                  ) : <span className="muted">aucune</span>}
                </dd>
              </div>
              {a.filtres && Object.keys(a.filtres).length > 0 && (
                <div><dt>Filtres</dt><dd className="mono small">{Object.entries(a.filtres).map(([k, v]) => `${k} = ${v}`).join(' · ')}</dd></div>
              )}
            </dl>
            {a.etapes && (
              <ol className="pipeline small">{a.etapes.map((s) => <li key={s.nom}><strong>{s.nom}</strong> — {s.detail}</li>)}</ol>
            )}
          </aside>

          {a.sparql && (
            <section className="panel answer-sparql">
              <p className="panel-title">Requête SPARQL générée</p>
              {a.explication?.length > 0 && <ul className="explain">{a.explication.map((x) => <li key={x}>{x}</li>)}</ul>}
              <CodeBlock code={a.sparql} />
            </section>
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
