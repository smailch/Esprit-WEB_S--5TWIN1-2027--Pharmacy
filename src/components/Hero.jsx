import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import MetricCard from './MetricCard.jsx';
import { scrollToId } from './Navbar.jsx';
import { HERO_VIDEO_SRC, HERO_POSTER_SRC, heroMetrics } from '../data/ontologyData.js';

export default function Hero() {
  const [videoOk, setVideoOk] = useState(true);
  const [reduce, setReduce] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduce(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  return (
    <section id="accueil" className="hero" aria-label="Accueil">
      <div className="hero-media" aria-hidden="true">
        <div className="hero-fallback" />
        {videoOk && !reduce && (
          <video
            className="hero-video"
            src={HERO_VIDEO_SRC}
            poster={HERO_POSTER_SRC}
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            onError={() => setVideoOk(false)}
          />
        )}
        <div className="hero-overlay" />
      </div>

      <div className="hero-content container">
        <div className="hero-copy">
          <p className="eyebrow stagger" style={{ '--d': '0.1s' }}>WEB SÉMANTIQUE · 5 TWIN · 2026–2027</p>
          <h1 className="hero-title stagger" style={{ '--d': '0.22s' }}>
            Comprendre le médicament.<br />
            <em>Connecter les connaissances.</em>
          </h1>
          <p className="hero-desc stagger" style={{ '--d': '0.36s' }}>
            Une ontologie pharmaceutique qui structure les connaissances sur les molécules, les effets secondaires,
            les contre-indications et les données cliniques.
          </p>
          <div className="hero-actions stagger" style={{ '--d': '0.5s' }}>
            <button type="button" className="btn btn-primary" onClick={() => scrollToId('ontologie')}>
              Explorer l’ontologie <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
            </button>
            <Link to="/molecules" className="btn btn-ghost">
              Ouvrir l’application
            </Link>
          </div>
          <div className="hero-metrics stagger" style={{ '--d': '0.64s' }}>
            {heroMetrics.map((m) => <MetricCard key={m.label} {...m} />)}
          </div>
          <p className="hero-note stagger" style={{ '--d': '0.74s' }}>
            Les 5 relations affichées sont les relations principales ; l’ontologie complète en définit davantage.
          </p>
        </div>
      </div>
    </section>
  );
}
