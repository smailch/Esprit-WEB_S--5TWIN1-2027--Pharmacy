import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { api } from './api';
import { useApi, useDebounced } from './hooks';
import { Async, Empty } from './ui';

const W = 760;
const H = 520;
const R = 200;

function Radial({ g }) {
  const go = useNavigate();
  const edges = g.edges.filter((e) => e.prop !== 'type' || e.dir === 'out');
  const n = edges.length;
  const cut = (s, k = 22) => (s && s.length > k ? `${s.slice(0, k - 1)}…` : s);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="graph" role="img" aria-label={`Graphe des relations de ${g.label}`}>
      {edges.map((e, i) => {
        const a = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
        const x = W / 2 + R * 1.45 * Math.cos(a);
        const y = H / 2 + R * Math.sin(a);
        const isClass = e.prop === 'type';
        return (
          <g key={`${e.dir}-${e.prop}-${e.id}`}>
            <line x1={W / 2} y1={H / 2} x2={x} y2={y} className={`edge ${e.dir}`} />
            <text x={(W / 2 + x) / 2} y={(H / 2 + y) / 2 - 4} className="edge-label">
              {e.dir === 'in' ? `← ${e.prop}` : `${e.prop} →`}
            </text>
            <g className={`node ${isClass ? 'class' : ''}`} tabIndex={isClass ? -1 : 0} role={isClass ? undefined : 'link'}
              onClick={() => !isClass && go(`/graphe/${e.id}`)}
              onKeyDown={(ev) => ev.key === 'Enter' && !isClass && go(`/graphe/${e.id}`)}>
              <title>{`${e.label || e.id} (:${e.id})`}</title>
              <circle cx={x} cy={y} r={isClass ? 7 : 10} />
              <text x={x} y={y + 24} textAnchor="middle">{cut(e.label || e.id)}</text>
            </g>
          </g>
        );
      })}
      <circle cx={W / 2} cy={H / 2} r={30} className="center" />
      <text x={W / 2} y={H / 2 + 48} textAnchor="middle" className="center-label">{g.label}</text>
    </svg>
  );
}

export default function Graphe({ id }) {
  const [q, setQ] = useState('');
  const dq = useDebounced(q);
  const results = useApi((signal) => (dq.length > 1 ? api.search(dq, { signal }) : Promise.resolve([])), [dq]);
  const graph = useApi((signal) => (id ? api.graph(id, { signal }) : Promise.resolve(null)), [id]);

  return (
    <>
      <h1>Graphe des relations</h1>
      <div className="toolbar">
        <input type="search" aria-label="Chercher une entité" placeholder="Chercher un patient, une pathologie, un médecin…"
          value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {results.data?.length > 0 && (
        <ul className="chips">
          {results.data.map((r) => <li key={r.id}><Link to={`/graphe/${r.id}`} onClick={() => setQ('')}>{r.label}</Link></li>)}
        </ul>
      )}
      {!id ? <Empty>Choisissez une entité (ou ouvrez le graphe depuis une fiche).</Empty> : (
        <Async state={graph}>
          {(g) => (
            <section className="card">
              <h2>{g.label} <code>:{g.id}</code></h2>
              <p className="muted small">Relations sortantes (→) et entrantes (←). Cliquez sur un nœud pour naviguer.</p>
              <Radial g={g} />
            </section>
          )}
        </Async>
      )}
    </>
  );
}
