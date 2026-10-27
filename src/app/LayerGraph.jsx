import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const LAYERS = [
  ['Medecin', 'Pharmacien', 'Patient'],
  ['Prescription', 'DonneeClinique'],
  ['Medicament'],
  ['Molecule'],
  ['ContreIndication'],
  ['Pathologie'],
];
const COLORS = {
  Prescription: 'var(--forest)', Patient: '#5b6b8c', Medecin: 'var(--green)', Pharmacien: '#6f7f5a',
  DonneeClinique: '#8a6f9e', Medicament: '#2f6b55', Molecule: '#4e8a5b', ContreIndication: 'var(--gold)', Pathologie: '#a0563b',
};
const TYPE_LABELS = {
  Prescription: 'Prescription', Patient: 'Patient', Medecin: 'Médecin', Pharmacien: 'Pharmacien',
  DonneeClinique: 'Donnée clinique', Medicament: 'Médicament', Molecule: 'Molécule', ContreIndication: 'Contre-indication', Pathologie: 'Pathologie',
};
const LINKS = { Prescription: '/prescriptions/', Patient: '/scenario?patient=', Medicament: '/medicaments/', Molecule: '/molecules/' };

/**
 * Graphe en colonnes d'une ordonnance (résultat d'une requête CONSTRUCT) :
 * personnes → prescription et données cliniques → médicaments → molécules → contre-indications → pathologies.
 * Conflit (en rouge) : pathologie atteinte par « concernePathologie » et par « souffreDe » ou « porteSur »,
 * ou molécule atteinte par « contientMolecule » et par « allergiqueA ».
 */
export default function LayerGraph({ data }) {
  const [hover, setHover] = useState(null);
  const navigate = useNavigate();
  const W = 980;

  const layout = useMemo(() => {
    if (!data) return null;
    const cols = LAYERS.map((types) => data.noeuds.filter((n) => types.includes(n.type)));
    const maxRows = Math.max(...cols.map((c) => c.length), 1);
    const TOP = 90; // marge pour les arcs « souffreDe »
    const H = Math.max(300, maxRows * 78 + 40 + TOP);
    const pos = {};
    cols.forEach((col, ci) => {
      const x = 80 + (ci * (W - 160)) / (LAYERS.length - 1);
      col.forEach((n, ri) => { pos[n.id] = { x, y: TOP + ((H - TOP) / (col.length + 1)) * (ri + 1) }; });
    });
    const targetsByRel = (rel) => new Set(data.aretes.filter((e) => e.relation === rel).map((e) => e.cible));
    const dossier = new Set([...targetsByRel('souffreDe'), ...targetsByRel('porteSur')]);
    const allergenes = targetsByRel('allergiqueA');
    const conflicts = new Set([
      ...[...targetsByRel('concernePathologie')].filter((p) => dossier.has(p)),
      ...[...targetsByRel('contientMolecule')].filter((m) => allergenes.has(m)),
    ]);
    return { pos, H, conflicts };
  }, [data]);

  if (!data || !layout) return null;
  if (!data.noeuds.length) return <p className="empty">Graphe vide.</p>;
  const { pos, H, conflicts } = layout;
  const on = (e) => hover && (e.source === hover || e.cible === hover);

  return (
    <figure className="result-graph layer-graph">
      <div className="table-scroll">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Graphe CONSTRUCT de ${data.centre}`} style={{ minWidth: 720 }}>
          <defs>
            <marker id="lg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10 z" fill="currentColor" />
            </marker>
          </defs>
          {data.aretes.map((e, i) => {
            const a = pos[e.source];
            const b = pos[e.cible];
            if (!a || !b) return null;
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const len = Math.hypot(dx, dy) || 1;
            const curve = ['souffreDe', 'porteSur', 'allergiqueA'].includes(e.relation);
            const mx = (a.x + b.x) / 2;
            // souffreDe / porteSur / allergiqueA relient des colonnes éloignées : l'arc passe au-dessus du graphe.
            const my = curve ? Math.min(a.y, b.y) - 70 : (a.y + b.y) / 2;
            const path = curve
              ? `M${a.x} ${a.y - 18} Q${mx} ${my} ${b.x - 6} ${b.y - 22}`
              : `M${a.x} ${a.y} L${b.x - (dx / len) * 26} ${b.y - (dy / len) * 26}`;
            const danger = curve && conflicts.has(e.cible);
            return (
              <g key={i} className={`rg-edge ${on(e) ? 'is-on' : ''} ${hover && !on(e) ? 'is-dim' : ''} ${danger ? 'is-danger' : ''}`}>
                <path d={path} fill="none" markerEnd="url(#lg-arrow)" />
                <text x={mx} y={(curve ? (Math.min(a.y, b.y) + my) / 2 : my - 6)} textAnchor="middle">{e.relation}</text>
              </g>
            );
          })}
          {data.noeuds.map((n) => {
            const p = pos[n.id];
            if (!p) return null;
            const link = LINKS[n.type];
            const label = n.label.length > 24 ? `${n.label.slice(0, 23)}…` : n.label;
            const go = () => link && n.id !== data.centre && navigate(link + n.id);
            return (
              <g
                key={n.id}
                className={`rg-node ${hover && hover !== n.id && !data.aretes.some((e) => on(e) && (e.source === n.id || e.cible === n.id)) ? 'is-dim' : ''}`}
                transform={`translate(${p.x} ${p.y})`}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(n.id)}
                onBlur={() => setHover(null)}
                tabIndex={link ? 0 : -1}
                role={link ? 'link' : undefined}
                aria-label={`${n.label} (${TYPE_LABELS[n.type] || 'ressource'})`}
                onClick={go}
                onKeyDown={(e) => e.key === 'Enter' && go()}
                style={{ cursor: link ? 'pointer' : 'default' }}
              >
                <circle r={n.id === data.centre ? 24 : 18} fill={conflicts.has(n.id) ? '#b0563b' : COLORS[n.type] || '#777'} className={conflicts.has(n.id) ? 'is-conflict' : ''} />
                <text y={n.id === data.centre ? 40 : 34} textAnchor="middle">{label}</text>
              </g>
            );
          })}
        </svg>
      </div>
      <figcaption className="legend-row">
        {Object.entries(TYPE_LABELS).map(([k, v]) => (
          <span key={k} className="legend-item"><span className="dot" style={{ background: COLORS[k] }} />{v}</span>
        ))}
        <span className="legend-item"><span className="dot" style={{ background: '#b0563b', outline: '2px solid #7a311b' }} />Conflit avec le dossier</span>
      </figcaption>
    </figure>
  );
}
