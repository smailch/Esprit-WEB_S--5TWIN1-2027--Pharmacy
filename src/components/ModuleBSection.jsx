import { useEffect, useState } from 'react';
import { Activity, ShieldAlert, MessageSquareText } from 'lucide-react';
import SectionHeading from './SectionHeading.jsx';
import { SUGGESTIONS, api } from '../api/moduleB.js';

const EMPTY_EFFECT = {
  id: '',
  label: '',
  type: 'EffetLegerDigestif',
  gravite: 'léger',
  frequence: '',
  molecules: '',
};

function Chip({ active, children, onClick }) {
  return (
    <button type="button" className={`chip ${active ? 'is-active' : ''}`} onClick={onClick}>
      {children}
    </button>
  );
}

function Banner({ kind = 'info', children }) {
  if (!children) return null;
  return <p className={`mb-banner ${kind === 'error' ? 'is-error' : ''}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</p>;
}

function ResultList({ items, empty, onOpen }) {
  if (!items) return <p className="muted">Chargement…</p>;
  if (!items.length) return <p className="muted">{empty}</p>;
  return (
    <ul className="mb-list">
      {items.map((item) => (
        <li key={item.id}>
          <button type="button" className="mb-row" onClick={() => onOpen(item)}>
            <span>
              <strong>{item.label}</strong>
              <span className="mb-meta">{item.type}{item.gravite ? ` · ${item.gravite}` : ''}{item.niveauRisque ? ` · ${item.niveauRisque}` : ''}{item.frequence ? ` · ${item.frequence}` : ''}</span>
            </span>
            <span className="tag tag-mono">{item.id}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function RelationList({ title, items, empty }) {
  return (
    <div>
      <p className="eyebrow">{title}</p>
      {items?.length ? (
        <ul className="tag-list">
          {items.map((item) => <li key={item.id} className="tag">{item.label}</li>)}
        </ul>
      ) : <p className="muted small">{empty}</p>}
    </div>
  );
}

export default function ModuleBSection() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState('');
  const [resources, setResources] = useState(null);
  const [gravite, setGravite] = useState('');
  const [effectCategory, setEffectCategory] = useState('');
  const [effectQuery, setEffectQuery] = useState('');
  const [effects, setEffects] = useState(null);
  const [effectsError, setEffectsError] = useState('');
  const [ciCategory, setCiCategory] = useState('');
  const [ciQuery, setCiQuery] = useState('');
  const [contraindications, setContraindications] = useState(null);
  const [ciError, setCiError] = useState('');
  const [finder, setFinder] = useState('Advil');
  const [finderKind, setFinderKind] = useState('medicament');
  const [foundEffects, setFoundEffects] = useState(null);
  const [foundCi, setFoundCi] = useState(null);
  const [finderError, setFinderError] = useState('');
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState('');
  const [question, setQuestion] = useState(SUGGESTIONS[0]);
  const [answer, setAnswer] = useState(null);
  const [askError, setAskError] = useState('');
  const [asking, setAsking] = useState(false);
  const [token, setToken] = useState('neocoders-module-b');
  const [draft, setDraft] = useState(EMPTY_EFFECT);
  const [crudKind, setCrudKind] = useState('effect');
  const [crudMessage, setCrudMessage] = useState('');
  const [crudError, setCrudError] = useState('');
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let cancel = false;
    api('/api/b/health')
      .then((data) => { if (!cancel) { setHealth(data); setHealthError(''); } })
      .catch((error) => { if (!cancel) setHealthError(error.message); });
    api('/api/b/ontology/resources')
      .then((data) => { if (!cancel) setResources(data); })
      .catch(() => {});
    return () => { cancel = true; };
  }, []);

  useEffect(() => {
    if (health || !effects) return undefined;
    let cancel = false;
    api('/api/b/health')
      .then((data) => { if (!cancel) { setHealth(data); setHealthError(''); } })
      .catch(() => {});
    return () => { cancel = true; };
  }, [effects, health]);

  useEffect(() => {
    let cancel = false;
    const params = new URLSearchParams();
    if (gravite) params.set('gravite', gravite);
    if (effectCategory) params.set('categorie', effectCategory);
    if (effectQuery.trim()) params.set('q', effectQuery.trim());
    setEffects(null);
    setEffectsError('');
    api(`/api/b/effects?${params.toString()}`)
      .then((data) => { if (!cancel) setEffects(data); })
      .catch((error) => { if (!cancel) setEffectsError(error.message); });
    return () => { cancel = true; };
  }, [gravite, effectCategory, effectQuery, revision]);

  useEffect(() => {
    let cancel = false;
    const params = new URLSearchParams();
    if (ciCategory) params.set('categorie', ciCategory);
    if (ciQuery.trim()) params.set('q', ciQuery.trim());
    setContraindications(null);
    setCiError('');
    api(`/api/b/contraindications?${params.toString()}`)
      .then((data) => { if (!cancel) setContraindications(data); })
      .catch((error) => { if (!cancel) setCiError(error.message); });
    return () => { cancel = true; };
  }, [ciCategory, ciQuery, revision]);

  async function openDetail(kind, id) {
    setDetailError('');
    setDetail(null);
    try {
      const path = kind === 'effect' ? `/api/b/effects/${id}` : `/api/b/contraindications/${id}`;
      const data = await api(path);
      setDetail({ kind, ...data });
    } catch (error) {
      setDetailError(error.message);
    }
  }

  async function runFinder(event) {
    event.preventDefault();
    setFinderError('');
    setFoundEffects(null);
    setFoundCi(null);
    const params = new URLSearchParams({ [finderKind]: finder.trim() });
    try {
      const [effectsData, ciData] = await Promise.all([
        api(`/api/b/effects?${params.toString()}`),
        api(`/api/b/contraindications?${params.toString()}`),
      ]);
      setFoundEffects(effectsData);
      setFoundCi(ciData);
    } catch (error) {
      setFinderError(error.message);
    }
  }

  async function runQuestion(event, preset) {
    event?.preventDefault();
    const text = (preset || question).trim();
    if (preset) setQuestion(preset);
    setAsking(true);
    setAskError('');
    try {
      setAnswer(await api('/api/b/nlp/ask', { method: 'POST', body: { question: text } }));
    } catch (error) {
      setAskError(error.message);
      setAnswer(null);
    } finally {
      setAsking(false);
    }
  }

  function splitIds(value) {
    return value.split(',').map((item) => item.trim()).filter(Boolean);
  }

  async function submitCrud(action) {
    setCrudError('');
    setCrudMessage('');
    const isEffect = crudKind === 'effect';
    const root = isEffect ? '/api/b/effects' : '/api/b/contraindications';
    try {
      if (action === 'delete') {
        if (!draft.id) throw new Error('Indiquez l’identifiant à supprimer.');
        const data = await api(`${root}/${draft.id}`, { method: 'DELETE', token });
        setCrudMessage(`Individu ${data.deleted} supprimé du graphe de travail.`);
      } else {
        const body = isEffect
          ? {
              ...(draft.id ? { id: draft.id } : {}),
              label: draft.label,
              type: draft.type,
              gravite: draft.gravite,
              ...(draft.frequence ? { frequence: draft.frequence } : {}),
              molecules: splitIds(draft.molecules || ''),
            }
          : {
              ...(draft.id ? { id: draft.id } : {}),
              label: draft.label,
              type: draft.type,
              niveauRisque: draft.niveauRisque || 'relatif',
              molecules: splitIds(draft.molecules || ''),
              pathologies: splitIds(draft.pathologies || ''),
            };
        const data = await api(action === 'create' ? root : `${root}/${draft.id}`, {
          method: action === 'create' ? 'POST' : 'PUT',
          body,
          token,
        });
        setCrudMessage(`${data.label} enregistré (${data.id}).`);
        setDraft((current) => ({ ...current, id: data.id }));
      }
      setRevision((value) => value + 1);
    } catch (error) {
      setCrudError(error.message);
    }
  }

  const effectTypes = resources?.effectTypes || [];
  const ciTypes = resources?.contraindicationTypes || [];
  const molecules = resources?.molecules || [];

  return (
    <section id="module-b" className="section section-tint">
      <div className="container">
        <SectionHeading label="MODULE B — ISMAIL" title="Effets secondaires et contre-indications.">
          <p>
            Cette partie interroge le graphe <code>pharma.ttl</code> via FastAPI et RDFLib.
            Un effet n’est pas relié directement à un médicament : le chemin asserté est{' '}
            <code>contientMolecule</code> puis <code>peutProvoquer</code>. Une contre-indication passe par{' '}
            <code>aContreIndication</code>.
          </p>
        </SectionHeading>

        <Banner kind={healthError ? 'error' : 'info'}>
          {healthError || (health
            ? `${health.triples} triplets chargés · ${health.llm?.detail || 'traducteur'} · analyse linguistique : ${health.spacy}. ${health.reasoning}`
            : 'Connexion à l’API…')}
        </Banner>
        {resources?.namingNote && <p className="disclaimer">{resources.namingNote}</p>}

        <div className="mb-grid">
          <article className="glass card">
            <header className="mb-title">
              <span className="icon-chip"><Activity size={18} /></span>
              <h3>Effets secondaires</h3>
            </header>
            <div className="mb-filters" role="group" aria-label="Filtrer par gravité">
              <Chip active={gravite === ''} onClick={() => setGravite('')}>Tous</Chip>
              <Chip active={gravite === 'léger'} onClick={() => setGravite('léger')}>Léger</Chip>
              <Chip active={gravite === 'grave'} onClick={() => setGravite('grave')}>Grave</Chip>
            </div>
            <div className="mb-filters" role="group" aria-label="Filtrer par catégorie">
              <Chip active={effectCategory === ''} onClick={() => setEffectCategory('')}>Toutes</Chip>
              <Chip active={effectCategory === 'digestif'} onClick={() => setEffectCategory('digestif')}>Digestif</Chip>
              <Chip active={effectCategory === 'cutane'} onClick={() => setEffectCategory('cutane')}>Cutané</Chip>
              <Chip active={effectCategory === 'neurologique'} onClick={() => setEffectCategory('neurologique')}>Neurologique</Chip>
            </div>
            <label className="field">
              Recherche
              <input value={effectQuery} onChange={(event) => setEffectQuery(event.target.value)} placeholder="nausée, convulsion…" />
            </label>
            <Banner kind="error">{effectsError}</Banner>
            {!effectsError && (
              <ResultList items={effects?.items} empty="Aucun effet ne correspond à ces filtres." onOpen={(item) => openDetail('effect', item.id)} />
            )}
            {effects && !effectsError && <p className="small muted">{effects.total} effet(s)</p>}
          </article>

          <article className="glass card">
            <header className="mb-title">
              <span className="icon-chip"><ShieldAlert size={18} /></span>
              <h3>Contre-indications</h3>
            </header>
            <div className="mb-filters" role="group" aria-label="Filtrer les contre-indications">
              {[
                ['', 'Toutes'],
                ['allergique', 'Allergique'],
                ['digestive', 'Digestive'],
                ['renale', 'Rénale'],
                ['hepatique', 'Hépatique'],
                ['absolue', 'Absolue'],
                ['relative', 'Relative'],
              ].map(([value, label]) => (
                <Chip key={label} active={ciCategory === value} onClick={() => setCiCategory(value)}>{label}</Chip>
              ))}
            </div>
            <label className="field">
              Recherche
              <input value={ciQuery} onChange={(event) => setCiQuery(event.target.value)} placeholder="rénale, pénicilline…" />
            </label>
            <Banner kind="error">{ciError}</Banner>
            {!ciError && (
              <ResultList
                items={contraindications?.items}
                empty="Aucune contre-indication ne correspond à ces filtres."
                onOpen={(item) => openDetail('contraindication', item.id)}
              />
            )}
            {contraindications && !ciError && <p className="small muted">{contraindications.total} contre-indication(s)</p>}
          </article>
        </div>

        <form className="glass card mb-block" onSubmit={runFinder}>
          <h3>Recherche par médicament ou molécule</h3>
          <div className="mb-inline">
            <label className="field">
              Type
              <select value={finderKind} onChange={(event) => setFinderKind(event.target.value)}>
                <option value="medicament">Médicament</option>
                <option value="molecule">Molécule</option>
              </select>
            </label>
            <label className="field">
              Identifiant de l’ontologie
              <input list="finder-values" value={finder} onChange={(event) => setFinder(event.target.value)} required />
              <datalist id="finder-values">
                {(finderKind === 'medicament' ? resources?.medicaments : resources?.molecules)?.map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </datalist>
            </label>
            <button className="btn btn-primary" type="submit">Chercher les liens</button>
          </div>
          <Banner kind="error">{finderError}</Banner>
          {foundEffects && (
            <div className="mb-grid">
              <div>
                <p className="eyebrow">Effets via peutProvoquer</p>
                <ResultList items={foundEffects.items} empty="Aucun effet asserté pour cet individu." onOpen={(item) => openDetail('effect', item.id)} />
              </div>
              <div>
                <p className="eyebrow">Contre-indications via aContreIndication</p>
                <ResultList items={foundCi?.items || []} empty="Aucune contre-indication assertée." onOpen={(item) => openDetail('contraindication', item.id)} />
              </div>
            </div>
          )}
        </form>

        <article className="glass card mb-block" aria-live="polite">
          <h3>Fiche et relations connues</h3>
          <Banner kind="error">{detailError}</Banner>
          {!detail && <p className="muted">Choisissez un effet ou une contre-indication dans les listes.</p>}
          {detail && (
            <div className="mb-detail">
              <div>
                <p className="eyebrow">{detail.kind === 'effect' ? 'EffetSecondaire' : 'ContreIndication'}</p>
                <h3>{detail.label}</h3>
                <p className="muted">{detail.typeLabel || detail.type} · <code>{detail.id}</code></p>
                {detail.note && <p className="disclaimer">{detail.note}</p>}
              </div>
              <RelationList title="Molécules" items={detail.molecules} empty="Aucune molécule assertée." />
              <RelationList title="Médicaments" items={detail.medicaments} empty="Aucun médicament ne contient ces molécules." />
              {detail.kind === 'contraindication' && (
                <RelationList title="Pathologies (concernePathologie)" items={detail.pathologies} empty="Aucune pathologie assertée." />
              )}
            </div>
          )}
        </article>

        <form className="glass card mb-block" onSubmit={runQuestion}>
          <header className="mb-title">
            <span className="icon-chip"><MessageSquareText size={18} /></span>
            <h3>Question en français</h3>
          </header>
          <p className="muted">
            Qwen2.5 3B Instruct, lancé en local par Ollama, écrit la requête SPARQL.
            Seules les lectures sont exécutées. Si le modèle n’est pas chargé, spaCy et les règles répondent à sa place.
          </p>
          <div className="mb-filters">
            {SUGGESTIONS.map((item) => (
              <button key={item} type="button" className="chip" onClick={(event) => runQuestion(event, item)}>{item}</button>
            ))}
          </div>
          <label className="field">
            Votre question
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={3} />
          </label>
          <button className="btn btn-primary" type="submit" disabled={asking}>{asking ? 'Analyse…' : 'Traduire et exécuter'}</button>
          <Banner kind="error">{askError}</Banner>
          {answer && (
            <div className="mb-answer">
              <p><strong>Intention :</strong> {answer.intent}</p>
              <p>{answer.message}</p>
              {!!answer.entities?.length && (
                <ul className="tag-list">
                  {answer.entities.map((entity) => (
                    <li key={`${entity.kind}-${entity.id}`} className="tag">{entity.kind} · {entity.label}</li>
                  ))}
                </ul>
              )}
              {!!answer.warnings?.length && answer.warnings.map((warning) => <p key={warning} className="disclaimer">{warning}</p>)}
              {answer.sparql ? <pre className="sparql">{answer.sparql}</pre> : <p className="muted">Aucune requête générée. Reformulez la question.</p>}
              {answer.intent === 'unknown' && (
                <ul className="tag-list">
                  {answer.suggestions?.map((item) => <li key={item} className="tag">{item}</li>)}
                </ul>
              )}
              <p className="small muted">{answer.count} résultat(s) · analyseur {answer.analysis?.analyzer}</p>
              {!!answer.results?.length && answer.results[0]?.count !== undefined && (
                <p className="metric-value">{answer.results[0].count}</p>
              )}
              {!!answer.results?.length && answer.results[0]?.verified !== undefined && (
                <p>{answer.results[0].verified ? 'Relation assertée dans le graphe.' : 'Relation absente du graphe.'} Chemin : <code>{answer.results[0].path}</code></p>
              )}
              {!!answer.results?.length && answer.results[0]?.label && (
                <ul className="mb-list">
                  {answer.results.map((item) => (
                    <li key={item.id || item.label} className="mb-row is-static">
                      <span>
                        <strong>{item.label}</strong>
                        <span className="mb-meta">
                          {item.nomCommercial ? `${item.nomCommercial} · ` : ''}
                          {(item.molecules || []).map((molecule) => molecule.label).join(', ')}
                          {(item.effects || item.contraindications || []).length ? ` → ${(item.effects || item.contraindications).map((effect) => effect.label).join(', ')}` : ''}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </form>

        <form className="glass card mb-block" onSubmit={(event) => { event.preventDefault(); submitCrud('create'); }}>
          <h3>Écriture contrôlée</h3>
          <p className="muted">
            Création, modification et suppression d’individus du module B. Le jeton de démonstration est attendu
            dans l’en-tête <code>X-Write-Token</code>. Les classes et propriétés hors liste blanche sont refusées.
            Le fichier source <code>ontologie/pharma.ttl</code> n’est pas modifié : l’écriture va dans la copie de travail.
          </p>
          <div className="mb-inline">
            <label className="field">
              Jeton
              <input type="password" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" />
            </label>
            <label className="field">
              Famille
              <select value={crudKind} onChange={(event) => {
                const kind = event.target.value;
                setCrudKind(kind);
                setDraft(kind === 'effect'
                  ? EMPTY_EFFECT
                  : { id: '', label: '', type: 'ContreIndicationRenale', niveauRisque: 'relatif', molecules: '', pathologies: '' });
              }}>
                <option value="effect">Effet secondaire</option>
                <option value="ci">Contre-indication</option>
              </select>
            </label>
            <label className="field">
              Identifiant
              <input value={draft.id || ''} onChange={(event) => setDraft({ ...draft, id: event.target.value })} placeholder="généré si vide, à la création" />
            </label>
          </div>
          <div className="mb-inline">
            <label className="field">
              Libellé
              <input value={draft.label || ''} onChange={(event) => setDraft({ ...draft, label: event.target.value })} required />
            </label>
            <label className="field">
              Classe réelle
              <select value={draft.type} onChange={(event) => setDraft({ ...draft, type: event.target.value })}>
                {(crudKind === 'effect' ? effectTypes : ciTypes).map((item) => (
                  <option key={item.id} value={item.id}>{item.label || item.id}</option>
                ))}
              </select>
            </label>
            {crudKind === 'effect' ? (
              <label className="field">
                Gravité
                <select value={draft.gravite || 'léger'} onChange={(event) => setDraft({ ...draft, gravite: event.target.value })}>
                  <option value="léger">léger</option>
                  <option value="grave">grave</option>
                </select>
              </label>
            ) : (
              <label className="field">
                Niveau de risque
                <select value={draft.niveauRisque || 'relatif'} onChange={(event) => setDraft({ ...draft, niveauRisque: event.target.value })}>
                  <option value="absolu">absolu</option>
                  <option value="relatif">relatif</option>
                </select>
              </label>
            )}
          </div>
          <div className="mb-inline">
            {crudKind === 'effect' && (
              <label className="field">
                Fréquence
                <input value={draft.frequence || ''} onChange={(event) => setDraft({ ...draft, frequence: event.target.value })} placeholder="rare" />
              </label>
            )}
            <label className="field">
              Molécules (identifiants séparés par des virgules)
              <input list="molecule-values" value={draft.molecules || ''} onChange={(event) => setDraft({ ...draft, molecules: event.target.value })} placeholder="Paracetamol" />
              <datalist id="molecule-values">
                {molecules.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </datalist>
            </label>
            {crudKind === 'ci' && (
              <label className="field">
                Pathologies
                <input value={draft.pathologies || ''} onChange={(event) => setDraft({ ...draft, pathologies: event.target.value })} placeholder="InsuffisanceRenale" />
              </label>
            )}
          </div>
          <div className="mb-filters">
            <button className="btn btn-primary" type="submit">Créer</button>
            <button className="btn btn-ghost" type="button" onClick={() => submitCrud('update')}>Modifier</button>
            <button className="btn btn-ghost" type="button" onClick={() => submitCrud('delete')}>Supprimer</button>
          </div>
          <Banner>{crudMessage}</Banner>
          <Banner kind="error">{crudError}</Banner>
        </form>

        <p className="disclaimer">
          Démonstration académique sur des individus fictifs. Ce module ne pose aucun diagnostic et ne recommande aucun traitement.
          RDFLib ne matérialise pas les équivalences OWL ni la chaîne de propriétés <code>estContreIndiquePour</code>.
        </p>
      </div>
    </section>
  );
}
