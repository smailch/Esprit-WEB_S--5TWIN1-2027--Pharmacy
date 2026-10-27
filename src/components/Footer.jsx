import Logo from './Logo.jsx';
import { scrollToId } from './Navbar.jsx';
import { navLinks } from '../data/ontologyData.js';

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div className="footer-brand">
          <span className="brand"><Logo /> <span>PharmaSémantique</span></span>
          <p>Ontologie Pharmaceutique et Santé</p>
          <p className="footer-meta">NeoCoders · 5 TWIN · 2026–2027</p>
        </div>
        <nav aria-label="Navigation du pied de page">
          <ul className="footer-links">
            {navLinks.map((l) => (
              <li key={l.id}>
                <a href={`#${l.id}`} onClick={(e) => { e.preventDefault(); scrollToId(l.id); }}>{l.label}</a>
              </li>
            ))}
            <li><a href="/ahmed.html">Pathologies &amp; Personnes (application)</a></li>
          </ul>
        </nav>
      </div>
      <div className="container footer-bottom">
        <p className="footer-thanks">Merci de votre visite.</p>
        <p className="footer-meta">Projet académique de Web Sémantique — données fictives, aucune recommandation médicale.</p>
      </div>
    </footer>
  );
}
