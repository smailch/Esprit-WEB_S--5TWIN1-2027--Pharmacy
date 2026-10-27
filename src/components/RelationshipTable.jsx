import { useState } from 'react';
import { ArrowRight, Info } from 'lucide-react';
import SectionHeading from './SectionHeading.jsx';
import { relations, datatypeProperties } from '../data/ontologyData.js';

export default function RelationshipTable() {
  const [active, setActive] = useState(0);
  const rel = relations[active];

  return (
    <section id="relations" className="section">
      <div className="container">
        <SectionHeading label="03 — RELATIONS" title="Les connaissances prennent sens grâce aux relations.">
          <p>
            Les propriétés d’objet (object properties) relient les entités de l’ontologie entre elles. Chacune
            possède un domaine (la classe de départ) et un range (la classe d’arrivée).
          </p>
        </SectionHeading>

        <div className="relations-layout">
          <div className="table-wrap glass" data-reveal>
            <table className="rel-table">
              <caption className="sr-only">Les cinq relations principales de l’ontologie</caption>
              <thead>
                <tr><th scope="col">Propriété</th><th scope="col">Domaine</th><th scope="col">Range</th></tr>
              </thead>
              <tbody>
                {relations.map((r, i) => (
                  <tr key={r.name} className={i === active ? 'is-active' : ''}>
                    <th scope="row">
                      <button type="button" className="rel-select" aria-pressed={i === active} onClick={() => setActive(i)}>
                        {r.name}
                      </button>
                    </th>
                    <td data-label="Domaine">{r.domain}</td>
                    <td data-label="Range">{r.range}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rel-explorer glass" data-reveal aria-live="polite">
            <p className="eyebrow">Explorateur de relation</p>
            <div className="rel-visual">
              <span className="rel-node is-domain">{rel.domain}</span>
              <span className="rel-arrow">
                <span className="rel-arrow-label">{rel.name}</span>
                <ArrowRight size={18} strokeWidth={1.4} aria-hidden="true" />
              </span>
              <span className="rel-node is-range">{rel.range}</span>
            </div>
            <p className="rel-sentence">{rel.sentence}</p>
            <div className="rel-chips" role="group" aria-label="Choisir une relation">
              {relations.map((r, i) => (
                <button key={r.name} type="button" className={`chip ${i === active ? 'is-active' : ''}`} aria-pressed={i === active} onClick={() => setActive(i)}>
                  {r.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        <aside className="note glass" data-reveal>
          <Info size={18} strokeWidth={1.4} aria-hidden="true" />
          <div>
            <p>
              Ces cinq relations sont les relations principales présentées. L’ontologie complète contient également des
              propriétés liées aux prescriptions, aux patients, aux professionnels de santé et aux modalités
              d’administration.
            </p>
            <p>
              La présentation identifie aussi <strong>{datatypeProperties.total} propriétés de données</strong> (datatype
              properties), dont :
            </p>
            <ul className="tag-list">
              {datatypeProperties.examples.map((p) => <li key={p} className="tag tag-mono">{p}</li>)}
            </ul>
          </div>
        </aside>
      </div>
    </section>
  );
}
