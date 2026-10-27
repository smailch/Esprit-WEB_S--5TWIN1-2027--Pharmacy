import { useEffect, useState } from 'react';
import { NavLink, Link, Outlet, useLocation } from 'react-router-dom';
import { FlaskConical, Pill, Scale, ShieldAlert, MessageSquareText, Database, Menu, X, Home, RotateCcw } from 'lucide-react';
import Logo from '../components/Logo.jsx';
import { api } from '../api/client.js';
import { useToast } from './Toast.jsx';

const links = [
  { to: '/molecules', label: 'Molécules', icon: FlaskConical },
  { to: '/medicaments', label: 'Médicaments', icon: Pill },
  { to: '/comparateur', label: 'Comparateur', icon: Scale },
  { to: '/interactions', label: 'Interactions', icon: ShieldAlert },
  { to: '/assistant', label: 'Assistant IA', icon: MessageSquareText },
  { to: '/sparql', label: 'Console SPARQL', icon: Database },
];

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState(null);
  const { pathname } = useLocation();
  const notify = useToast();

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    // Vérifie l'API à chaque page et toutes les 10 s (le back-end peut démarrer après le front).
    const check = () => api.health().then(setHealth).catch(() => setHealth({ statut: 'hors ligne' }));
    check();
    const t = setInterval(check, 10000);
    return () => clearInterval(t);
  }, [pathname]);

  const reset = async () => {
    if (!window.confirm('Recharger l’ontologie d’origine ? Toutes les modifications CRUD seront annulées.')) return;
    try {
      await api.reset();
      notify('Données réinitialisées depuis pharma.ttl');
      window.location.reload();
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  const online = health && health.statut === 'ok';

  return (
    <div className="app">
      <header className="app-top">
        <Link to="/" className="brand" aria-label="Retour à l’accueil PharmaSémantique">
          <Logo size={28} />
          <span>PharmaSémantique</span>
        </Link>
        <span className="app-module-tag">Module A · Molécule + Médicament</span>
        <button type="button" className="nav-toggle app-toggle" aria-expanded={open} aria-controls="app-nav" aria-label={open ? 'Fermer le menu' : 'Ouvrir le menu'} onClick={() => setOpen((v) => !v)}>
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      <div className="app-body">
        <aside id="app-nav" className={`app-nav ${open ? 'is-open' : ''}`} aria-label="Navigation de l’application">
          <nav>
            <ul>
              {links.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink to={to} className={({ isActive }) => `app-link ${isActive ? 'is-active' : ''}`}>
                    <Icon size={18} strokeWidth={1.5} aria-hidden="true" /> {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="app-nav-foot">
            <div className={`status ${online ? 'is-ok' : 'is-ko'}`}>
              <span className="status-dot" aria-hidden="true" />
              {online ? (
                <span>API connectée · {health.triplets_declares} triplets déclarés · {health.triplets_inferes} inférés</span>
              ) : (
                <span>{health ? 'API hors ligne — lancez le back-end' : 'Connexion…'}</span>
              )}
            </div>
            <button type="button" className="btn-link" onClick={reset}><RotateCcw size={14} aria-hidden="true" /> Réinitialiser les données</button>
            <Link to="/" className="btn-link"><Home size={14} aria-hidden="true" /> Site vitrine</Link>
          </div>
        </aside>

        <main className="app-main" id="contenu">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
