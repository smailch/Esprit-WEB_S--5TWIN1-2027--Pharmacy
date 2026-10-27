import SectionHeading from './SectionHeading.jsx';
import Icon from './Icon.jsx';
import { approachCards } from '../data/ontologyData.js';

export default function ApproachSection() {
  return (
    <section id="approche" className="section">
      <div className="container">
        <SectionHeading label="01 — NOTRE APPROCHE" title="Donner du sens aux données de santé.">
          <p>
            Le projet vise à représenter les connaissances pharmaceutiques et cliniques dans une structure formelle,
            afin de relier les médicaments, leurs substances actives, leurs effets secondaires, les contre-indications
            et les pathologies.
          </p>
        </SectionHeading>
        <div className="grid grid-4">
          {approachCards.map((c, i) => (
            <article key={c.title} className="glass card lift" data-reveal style={{ '--d': `${i * 0.08}s` }}>
              <span className="icon-chip"><Icon name={c.icon} /></span>
              <h3>{c.title}</h3>
              <p>{c.text}</p>
            </article>
          ))}
        </div>
        <p className="disclaimer" data-reveal>
          Projet académique de représentation des connaissances : il ne réalise aucun diagnostic et ne fournit aucune
          recommandation médicale validée.
        </p>
      </div>
    </section>
  );
}
