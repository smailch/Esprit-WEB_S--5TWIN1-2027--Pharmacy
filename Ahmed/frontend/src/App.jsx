import { useState } from 'react';
import { api } from './api/client';
import { useApi, useRoute } from './hooks';
import Dashboard from './pages/Dashboard';
import Pathologies from './pages/Pathologies';
import Personnes from './pages/Personnes';
import PatientFiche from './pages/PatientFiche';
import Assistant from './pages/Assistant';
import Graphe from './pages/Graphe';
import Console from './pages/Console';

const NAV = [
  ['', 'Tableau de bord'],
  ['pathologies', 'Pathologies'],
  ['personnes', 'Personnes'],
  ['assistant', 'Assistant NLP'],
  ['graphe', 'Graphe'],
  ['console', 'Console SPARQL'],
];

function Page({ route }) {
  const [first, second] = route.parts;
  switch (first) {
    case 'pathologies': return <Pathologies />;
    case 'personnes': return <Personnes tab={route.query.get('tab') || 'patients'} />;
    case 'patients': return <PatientFiche id={second} />;
    case 'assistant': return <Assistant initial={route.query.get('q')} />;
    case 'graphe': return <Graphe id={second} />;
    case 'console': return <Console />;
    default: return <Dashboard />;
  }
}

export default function App() {
  const route = useRoute();
  const health = useApi((signal) => api.health({ signal }), []);
  const [resetting, setResetting] = useState(false);
  const current = route.parts[0] === 'patients' ? 'personnes' : route.parts[0] || '';

  const reset = async () => {
    if (!window.confirm('Remettre toutes les données dans leur état initial ?')) return;
    setResetting(true);
    try {
      await api.reset();
      window.location.reload();
    } finally {
      setResetting(false);
    }
  };

  return (
    <>
      <a className="skip-link" href="#main">Aller au contenu</a>
      <header className="topbar">
        <div className="container topbar-inner">
          <a className="brand" href="#/">
            <span className="brand-mark" aria-hidden="true">℞</span>
            <span>PharmaSémantique <small>Pathologies &amp; Personnes</small></span>
          </a>
          <nav aria-label="Navigation principale">
            {NAV.map(([path, label]) => (
              <a key={path} href={`#/${path}`} aria-current={current === path ? 'page' : undefined}>{label}</a>
            ))}
          </nav>
        </div>
      </header>

      {health.error && (
        <div className="offline" role="alert">
          Backend injoignable : lancez <code>uvicorn app.main:app</code> dans <code>Ahmed/backend</code>.
          <button className="btn small" onClick={health.reload}>Réessayer</button>
        </div>
      )}

      <main id="main" className="container main">
        <Page route={route} />
      </main>

      <footer className="footer container">
        <p><strong>Données fictives — aucun conseil médical.</strong> Projet Web sémantique, ESPRIT 5 TWIN — Ahmed Allaya (NeoCoders).</p>
        <p className="muted small">
          {health.data ? `Triplestore : ${health.data.backend} · ${health.data.triples} triplets` : ''}
          <button className="link-btn" onClick={reset} disabled={resetting}>Réinitialiser les données</button>
        </p>
      </footer>
    </>
  );
}
