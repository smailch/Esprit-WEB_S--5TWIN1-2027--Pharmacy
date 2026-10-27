import { useMemo, useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import SectionHeading from './SectionHeading.jsx';
import { graphNodes, graphEdges } from '../data/ontologyData.js';

const W = 900;
const H = 560;
const nodeWidth = (label) => Math.max(96, label.length * 8.4 + 30);

export default function OntoGraphSection() {
  const [hovered, setHovered] = useState(null);
  const [selected, setSelected] = useState('SubstanceActive');
  const [zoom, setZoom] = useState(1);

  const byId = useMemo(() => Object.fromEntries(graphNodes.map((n) => [n.id, n])), []);
  const focus = hovered || selected;
  const linked = (e) => focus && (e.from === focus || e.to === focus);
  const neighbours = useMemo(() => {
    const s = new Set();
    graphEdges.forEach((e) => {
      if (e.from === focus) s.add(e.to);
      if (e.to === focus) s.add(e.from);
    });
    return s;
  }, [focus]);

  const sel = selected && byId[selected];
  const selEdges = graphEdges.filter((e) => e.from === selected || e.to === selected);

  const onKey = (e, id) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setSelected(id);
    }
  };

  // Zoom autour du centre de la vue.
  const tx = (W / 2) * (1 - zoom);
  const ty = (H / 2) * (1 - zoom);

  return (
    <section id="ontographe" className="section">
      <div className="container">
        <SectionHeading label="05 — VISUALISATION" title="Explorer les liens entre les connaissances.">
          <p>Survolez un nœud pour mettre en évidence ses connexions ; cliquez ou appuyez sur Entrée pour afficher ses détails.</p>
        </SectionHeading>

        <div className="graph-layout" data-reveal>
          <div className="graph-frame glass">
            <div className="graph-controls" role="group" aria-label="Contrôles du zoom">
              <button type="button" className="icon-btn" aria-label="Zoom avant" onClick={() => setZoom((z) => Math.min(1.8, +(z + 0.2).toFixed(2)))}><ZoomIn size={16} /></button>
              <button type="button" className="icon-btn" aria-label="Zoom arrière" onClick={() => setZoom((z) => Math.max(0.6, +(z - 0.2).toFixed(2)))}><ZoomOut size={16} /></button>
              <button type="button" className="icon-btn" aria-label="Réinitialiser la vue" onClick={() => { setZoom(1); setSelected(null); }}><RotateCcw size={16} /></button>
            </div>
            <div className="graph-scroll">
              <svg viewBox={`0 0 ${W} ${H}`} className="graph-svg" role="group" aria-label="Ontographe interactif des classes et individus">
                <defs>
                  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M0 0 L10 5 L0 10 z" fill="currentColor" />
                  </marker>
                </defs>
                <g transform={`translate(${tx} ${ty}) scale(${zoom})`}>
                  {graphEdges.map((e) => {
                    const a = byId[e.from];
                    const b = byId[e.to];
                    const on = linked(e);
                    const dim = focus && !on;
                    // Raccourcir la ligne pour que la flèche s'arrête au bord du nœud.
                    const dx = b.x - a.x;
                    const dy = b.y - a.y;
                    const len = Math.hypot(dx, dy) || 1;
                    const pad = 26;
                    const x1 = a.x + (dx / len) * pad;
                    const y1 = a.y + (dy / len) * pad;
                    const x2 = b.x - (dx / len) * pad;
                    const y2 = b.y - (dy / len) * pad;
                    const mx = (a.x + b.x) / 2;
                    const my = (a.y + b.y) / 2;
                    return (
                      <g key={`${e.from}-${e.to}`} className={`edge ${on ? 'is-on' : ''} ${dim ? 'is-dim' : ''} ${e.type ? 'is-type' : ''} ${e.dashed ? 'is-dashed' : ''}`}>
                        <line x1={x1} y1={y1} x2={x2} y2={y2} markerEnd="url(#arrow)" />
                        <text x={mx} y={my - 6} textAnchor="middle" className="edge-label">{e.label}</text>
                      </g>
                    );
                  })}
                  {graphNodes.map((n) => {
                    const w = nodeWidth(n.id);
                    const isFocus = n.id === focus;
                    const dim = focus && !isFocus && !neighbours.has(n.id);
                    return (
                      <g
                        key={n.id}
                        className={`node node-${n.kind} ${isFocus ? 'is-focus' : ''} ${n.id === selected ? 'is-selected' : ''} ${dim ? 'is-dim' : ''}`}
                        transform={`translate(${n.x} ${n.y})`}
                        tabIndex={0}
                        role="button"
                        aria-label={`${n.id}, ${n.kind === 'class' ? 'classe' : `individu de ${n.of}`}`}
                        aria-pressed={n.id === selected}
                        onMouseEnter={() => setHovered(n.id)}
                        onMouseLeave={() => setHovered(null)}
                        onFocus={() => setHovered(n.id)}
                        onBlur={() => setHovered(null)}
                        onClick={() => setSelected(n.id)}
                        onKeyDown={(e) => onKey(e, n.id)}
                      >
                        <rect x={-w / 2} y={-20} width={w} height={40} rx={n.kind === 'class' ? 20 : 8} />
                        <text textAnchor="middle" dy="5">{n.id}</text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            </div>
          </div>

          <aside className="graph-side">
            <div className="glass graph-info" aria-live="polite">
              {sel ? (
                <>
                  <p className="eyebrow">{sel.kind === 'class' ? 'Classe' : 'Individu'}</p>
                  <h3>{sel.id}</h3>
                  {sel.of && <p className="muted">Instance de {sel.of}</p>}
                  <ul className="graph-rels">
                    {selEdges.map((e) => (
                      <li key={`${e.from}-${e.to}`}>
                        <span>{e.from}</span> <code>{e.label}</code> <span>{e.to}</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="muted">Sélectionnez un nœud pour afficher son nom, son type et ses relations.</p>
              )}
            </div>
            <div className="glass graph-legend" aria-label="Légende du graphe">
              <span className="legend-item"><span className="swatch swatch-class" />Classe</span>
              <span className="legend-item"><span className="swatch swatch-ind" />Individu</span>
              <span className="legend-item"><span className="line-key" />Relation principale</span>
              <span className="legend-item"><span className="line-key is-dashed" />Lien de l’exemple Patient_F001</span>
              <span className="legend-item"><span className="line-key is-type" />Instance de</span>
            </div>
          </aside>
        </div>

        <p className="note-plain" data-reveal>
          L’ontographe permet de visualiser les relations entre les éléments de l’ontologie. La validation logique est
          réalisée séparément avec le raisonneur HermiT.
        </p>
        <p className="muted small" data-reveal>
          Visualisation web des concepts documentés dans la présentation du projet — il ne s’agit pas d’une capture de
          l’ontologie Protégé.
        </p>
      </div>
    </section>
  );
}
