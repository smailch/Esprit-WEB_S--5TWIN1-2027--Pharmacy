import SectionHeading from './SectionHeading.jsx';
import Icon from './Icon.jsx';
import { validationSteps } from '../data/ontologyData.js';

export default function ValidationSection() {
  return (
    <section id="validation" className="section section-tint">
      <div className="container">
        <SectionHeading label="06 — VALIDATION" title="Structurer, vérifier, comprendre.">
          <p>Le flux de travail de l’ontologie s’appuie sur Protégé pour la modélisation et sur HermiT pour le raisonnement.</p>
        </SectionHeading>
        <ol className="timeline">
          {validationSteps.map((s, i) => (
            <li key={s.title} className="timeline-step" data-reveal style={{ '--d': `${i * 0.1}s` }}>
              <span className="timeline-dot"><Icon name={s.icon} size={18} /></span>
              <span className="timeline-num">{String(i + 1).padStart(2, '0')}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </li>
          ))}
        </ol>
        <p className="muted small" data-reveal>
          Le raisonnement HermiT fait partie du processus de validation de l’ontologie ; il n’est pas exécuté dans ce site.
        </p>
      </div>
    </section>
  );
}
