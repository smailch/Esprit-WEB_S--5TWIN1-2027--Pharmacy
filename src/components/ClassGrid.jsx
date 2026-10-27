import { useState } from 'react';
import { Plus, Minus } from 'lucide-react';
import Icon from './Icon.jsx';
import { ontologyClasses } from '../data/ontologyData.js';

function ClassCard({ cls, index }) {
  const [open, setOpen] = useState(false);
  const panelId = `class-detail-${index}`;

  return (
    <article className={`glass class-card lift ${open ? 'is-open' : ''}`} data-reveal style={{ '--d': `${(index % 4) * 0.06}s` }}>
      <div className="class-card-head">
        <span className="icon-chip"><Icon name={cls.icon} /></span>
        <span className="class-index">{String(index + 1).padStart(2, '0')}</span>
      </div>
      <h3 className="class-name">{cls.id}</h3>
      <p className="class-summary">{cls.summary}</p>

      <ul className="tag-list" aria-label={`Sous-classes de ${cls.id}`}>
        {cls.subclasses.map((s) => (
          <li key={s.name} className="tag tag-sub">
            {s.name}
            {s.children && (
              <ul className="tag-children" aria-label={`Sous-classes de ${s.name}`}>
                {s.children.map((c) => <li key={c} className="tag tag-subsub">{c}</li>)}
              </ul>
            )}
          </li>
        ))}
      </ul>

      <button
        type="button"
        className="class-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <Minus size={14} aria-hidden="true" /> : <Plus size={14} aria-hidden="true" />}
        {open ? 'Masquer' : 'En savoir plus'}
      </button>
      <div id={panelId} className="class-detail" hidden={!open}>
        <p>{cls.detail}</p>
      </div>
    </article>
  );
}

export default function ClassGrid() {
  return (
    <div className="grid grid-4 class-grid">
      {ontologyClasses.map((cls, i) => <ClassCard key={cls.id} cls={cls} index={i} />)}
    </div>
  );
}
