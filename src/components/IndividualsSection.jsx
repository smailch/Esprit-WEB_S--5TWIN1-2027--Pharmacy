import { ArrowRight, ArrowDown, AlertTriangle } from 'lucide-react';
import SectionHeading from './SectionHeading.jsx';
import Icon from './Icon.jsx';
import { individualGroups, exampleFlow } from '../data/ontologyData.js';

export default function IndividualsSection() {
  return (
    <section id="individus" className="section section-tint">
      <div className="container">
        <SectionHeading label="04 — INSTANCES" title="Des concepts abstraits aux exemples concrets.">
          <p>
            Une <strong>classe</strong> décrit une catégorie générale (par exemple Médicament). Un{' '}
            <strong>individu</strong> est un élément concret appartenant à cette classe (par exemple Doliprane). Tous les
            individus ci-dessous sont des exemples de démonstration.
          </p>
        </SectionHeading>

        <div className="grid grid-3 ind-grid">
          {individualGroups.map((g, i) => (
            <article key={g.label} className="glass ind-card lift" data-reveal style={{ '--d': `${(i % 3) * 0.06}s` }}>
              <header className="ind-head">
                <span className="icon-chip"><Icon name={g.icon} size={18} /></span>
                <div>
                  <h3>{g.label}</h3>
                  <p className="ind-class">{g.cls}</p>
                </div>
                <span className="ind-count" aria-label={`${g.items.length} exemples`}>{g.items.length}</span>
              </header>
              <ul className="tag-list">
                {g.items.map((it) => <li key={it} className="tag tag-ind">{it}</li>)}
              </ul>
            </article>
          ))}
        </div>

        <div className="flow glass" data-reveal>
          <p className="eyebrow">Exemple illustratif</p>
          <ol className="flow-steps">
            {exampleFlow.map((s, i) => (
              <li key={s.name} className="flow-step">
                <span className="flow-node">
                  <span className="flow-name">{s.name}</span>
                  <span className="flow-type">{s.type}</span>
                </span>
                {i < exampleFlow.length - 1 && (
                  <span className="flow-arrow" aria-hidden="true">
                    <ArrowRight className="only-wide" size={18} strokeWidth={1.4} />
                    <ArrowDown className="only-narrow" size={18} strokeWidth={1.4} />
                  </span>
                )}
              </li>
            ))}
          </ol>

          <div className="flow-link">
            <span className="flow-node is-warn">
              <span className="flow-name">CI_Ulcère_Gastrique</span>
              <span className="flow-type">ContreIndication · concernePathologie → Ulcère_Gastrique</span>
            </span>
            <p>
              <AlertTriangle size={16} strokeWidth={1.5} aria-hidden="true" /> L’Ibuprofène est relié à la
              contre-indication CI_Ulcère_Gastrique par <code>aPourContreIndication</code>. Si les axiomes et contraintes
              correspondants sont correctement définis — par exemple, si le patient fictif est associé à la pathologie
              Ulcère_Gastrique — un raisonneur logique comme HermiT peut signaler l’incohérence de cette prescription.
            </p>
          </div>

          <p className="disclaimer">
            Exemple académique construit avec des individus fictifs : il ne s’agit ni d’une prescription réelle, ni
            d’une recommandation médicale.
          </p>
        </div>
      </div>
    </section>
  );
}
