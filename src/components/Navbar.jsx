import { useEffect, useState } from 'react';
import { Menu, X, ArrowUpRight } from 'lucide-react';
import Logo from './Logo.jsx';
import { navLinks } from '../data/ontologyData.js';

export function scrollToId(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
}

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open]);

  const go = (e, id) => {
    e.preventDefault();
    setOpen(false);
    scrollToId(id);
  };

  return (
    <header className={`navbar ${scrolled || open ? 'is-scrolled' : ''}`}>
      <nav className="nav-inner" aria-label="Navigation principale">
        <a href="#accueil" className="brand" onClick={(e) => go(e, 'accueil')} aria-label="PharmaSémantique, retour à l’accueil">
          <Logo />
          <span>PharmaSémantique</span>
        </a>

        <ul className="nav-links">
          {navLinks.map((l) => (
            <li key={l.id}>
              <a href={`#${l.id}`} onClick={(e) => go(e, l.id)}>{l.label}</a>
            </li>
          ))}
        </ul>

        <a href="#ontologie" className="btn btn-compact nav-cta" onClick={(e) => go(e, 'ontologie')}>
          Explorer le projet <ArrowUpRight size={15} strokeWidth={1.6} aria-hidden="true" />
        </a>

        <button
          type="button"
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label={open ? 'Fermer le menu' : 'Ouvrir le menu'}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={22} strokeWidth={1.5} /> : <Menu size={22} strokeWidth={1.5} />}
        </button>
      </nav>

      <div id="mobile-menu" className="mobile-menu" hidden={!open}>
        <ul>
          {navLinks.map((l) => (
            <li key={l.id}>
              <a href={`#${l.id}`} onClick={(e) => go(e, l.id)}>{l.label}</a>
            </li>
          ))}
        </ul>
        <a href="#ontologie" className="btn btn-primary" onClick={(e) => go(e, 'ontologie')}>Explorer le projet</a>
      </div>
    </header>
  );
}
