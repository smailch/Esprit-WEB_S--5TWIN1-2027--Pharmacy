import SectionHeading from './SectionHeading.jsx';
import { team } from '../data/ontologyData.js';

const initials = (name) => name.split(' ').map((p) => p[0]).join('').toUpperCase();

export default function TeamSection() {
  return (
    <section id="equipe" className="section">
      <div className="container">
        <SectionHeading label="ÉQUIPE NEOCODERS" title="Un projet collaboratif." />
        <ul className="grid grid-4 team-grid">
          {team.map((name, i) => (
            <li key={name} className="glass team-card lift" data-reveal style={{ '--d': `${i * 0.08}s` }}>
              <span className="avatar" aria-hidden="true">{initials(name)}</span>
              <span className="team-name">{name}</span>
              <span className="muted small">NeoCoders</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
