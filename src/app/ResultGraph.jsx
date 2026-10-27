import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const COLORS = {
  Medicament: 'var(--forest)',
  Molecule: 'var(--green)',
  EffetSecondaire: '#a0563b',
  ContreIndication: 'var(--gold)',
  Pathologie: '#5b6b8c',
};
const TYPE_LABELS = { Medicament: 'Médicament', Molecule: 'Molécule', EffetSecondaire: 'Effet secondaire', ContreIndication: 'Contre-indication', Pathologie: 'Pathologie' };

/**
 * Graphe radial d'un médicament (résultat d'une requête CONSTRUCT).
 * Anneau 1 : molécules ; anneau 2 : effets, contre-indications, pathologies, molécules en interaction.
 */
export default function ResultGraph({ data }) {
  const [hover, setHover] = useState(null);
  const navigate = useNavigate();
  const W = 760;
  const H = 520;

  const layout = useMemo(() => {
    if (!data) return null;
    const pos = {};
    const cx = W / 2;
    const cy = H / 2;
    pos[data.centre] = { x: cx, y: cy };
    const ring1 = data.noeuds.filter((n) => n.type === 'Molecule' && data.aretes.some((e) => e.source === data.centre && e.cible === n.id));
    ring1.forEach((n, i) => {
      const a = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(ring1.length, 1) + (ring1.length === 1 ? 0 : 0);
      pos[n.id] = { x: cx + Math.cos(a) * 120, y: cy + Math.sin(a) * 120 };
    });
    const rest = data.noeuds.filter((n) => !pos[n.id]);
    rest.forEach((n, i) => {
      const a = -Math.PI / 2 + Math.PI / rest.length + (i * 2 * Math.PI) / Math.max(rest.length, 1);
      pos[n.id] = { x: cx + Math.cos(a) * 225, y: cy + Math.sin(a) * 205 };
    });
    return pos;
  }, [data]);

  if (!data || !layout) return null;
  const linked = (e) => hover && (e.source === hover || e.cible === hover);

  return (
    <figure className="result-graph">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Graphe des relations de ${data.centre}`}>
        <defs>
          <marker id="rg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill="currentColor" />
          </marker>
        </defs>
        {data.aretes.map((e, i) => {
          const a = layout[e.source];
          const b = layout[e.cible];
          if (!a || !b) return null;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.hypot(dx, dy) || 1;
          const x2 = b.x - (dx / len) * 30;
          const y2 = b.y - (dy / len) * 30;
          return (
            <g key={i} className={`rg-edge ${linked(e) ? 'is-on' : ''} ${hover && !linked(e) ? 'is-dim' : ''}`}>
              <line x1={a.x} y1={a.y} x2={x2} y2={y2} markerEnd="url(#rg-arrow)" />
              <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 5} textAnchor="middle">{e.relation}</text>
            </g>
          );
        })}
        {data.noeuds.map((n) => {
          const p = layout[n.id];
          const clickable = n.type === 'Medicament' || n.type === 'Molecule';
          const label = n.label.length > 22 ? `${n.label.slice(0, 21)}…` : n.label;
          return (
            <g
              key={n.id}
              className={`rg-node ${hover && hover !== n.id && !data.aretes.some((e) => linked(e) && (e.source === n.id || e.cible === n.id)) ? 'is-dim' : ''}`}
              transform={`translate(${p.x} ${p.y})`}
              onMouseEnter={() => setHover(n.id)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(n.id)}
              onBlur={() => setHover(null)}
              tabIndex={clickable ? 0 : -1}
              role={clickable ? 'link' : undefined}
              aria-label={`${n.label} (${TYPE_LABELS[n.type] || 'ressource'})`}
              onClick={() => clickable && n.id !== data.centre && navigate(`/${n.type === 'Molecule' ? 'molecules' : 'medicaments'}/${n.id}`)}
              onKeyDown={(e) => e.key === 'Enter' && clickable && navigate(`/${n.type === 'Molecule' ? 'molecules' : 'medicaments'}/${n.id}`)}
              style={{ cursor: clickable ? 'pointer' : 'default' }}
            >
              <circle r={n.id === data.centre ? 30 : 22} fill={COLORS[n.type] || '#777'} />
              <text y={n.id === data.centre ? 46 : 38} textAnchor="middle">{label}</text>
            </g>
          );
        })}
      </svg>
      <figcaption className="legend-row">
        {Object.entries(TYPE_LABELS).map(([k, v]) => (
          <span key={k} className="legend-item"><span className="dot" style={{ background: COLORS[k] }} />{v}</span>
        ))}
      </figcaption>
    </figure>
  );
}
