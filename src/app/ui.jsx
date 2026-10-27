import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Code2, Copy, Download, Loader2, AlertTriangle, X, Sparkles } from 'lucide-react';

export function PageHeader({ eyebrow, title, children, actions }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {children && <div className="page-intro">{children}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Loading({ label = 'Chargement…' }) {
  return <p className="loading"><Loader2 size={18} className="spin" aria-hidden="true" /> {label}</p>;
}

export function ErrorBox({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="error-box" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <span>{message}</span>
      {onRetry && <button type="button" className="btn btn-compact" onClick={onRetry}>Réessayer</button>}
    </div>
  );
}

export function Empty({ children = 'Aucun résultat.' }) {
  return <p className="empty">{children}</p>;
}

export function Badge({ children, tone = 'neutral', title }) {
  return <span className={`badge badge-${tone}`} title={title}>{children}</span>;
}

export function InferredBadge() {
  return (
    <Badge tone="gold" title="Déduit par le raisonneur OWL 2 RL — non déclaré dans l’ontologie">
      <Sparkles size={11} aria-hidden="true" /> inféré
    </Badge>
  );
}

export const CLASS_LABELS = {
  Molecule: 'Molécule', Antibiotique: 'Antibiotique', Penicilline: 'Pénicilline', Macrolide: 'Macrolide',
  Antalgique: 'Antalgique', AntalgiqueNonOpioide: 'Antalgique non opioïde', AntalgiqueOpioide: 'Antalgique opioïde',
  Medicament: 'Médicament', Princeps: 'Princeps', Generique: 'Générique',
  PrincepsSurOrdonnance: 'Princeps sur ordonnance', PrincepsSansOrdonnance: 'Princeps sans ordonnance',
  GeneriqueSurOrdonnance: 'Générique sur ordonnance', GeneriqueSansOrdonnance: 'Générique sans ordonnance',
};

export const fmtPrix = (v) => (v === null || v === undefined ? '—' : `${Number(v).toFixed(2).replace('.', ',')} DT`);

/* ---------- Coloration syntaxique SPARQL minimaliste ---------- */
const KEYWORDS = /\b(PREFIX|SELECT|DISTINCT|WHERE|FILTER|OPTIONAL|UNION|GRAPH|VALUES|BIND|AS|ORDER|BY|GROUP|HAVING|ASK|CONSTRUCT|INSERT|DELETE|DATA|NOT|EXISTS|COUNT|AVG|MIN|MAX|SUM|GROUP_CONCAT|REGEX|STR|STRAFTER|STRSTARTS|LCASE|CONTAINS|ROUND|isIRI|DESC|ASC|LIMIT|true|false|a)\b/g;

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export function highlightSparql(code) {
  // Découpe en jetons (commentaires, chaînes, IRI) pour ne pas colorer l'intérieur des littéraux.
  const tokens = code.split(/(#[^\n]*|"(?:[^"\\]|\\.)*"(?:@\w+|\^\^\S+)?|<[^>\s]*>)/g);
  return tokens.map((t, i) => {
    if (i % 2 === 1) {
      if (t.startsWith('#')) return `<span class="tk-comment">${escapeHtml(t)}</span>`;
      if (t.startsWith('"')) return `<span class="tk-string">${escapeHtml(t)}</span>`;
      return `<span class="tk-iri">${escapeHtml(t)}</span>`;
    }
    return escapeHtml(t)
      .replace(KEYWORDS, '<span class="tk-kw">$1</span>')
      .replace(/(\?\w+)/g, '<span class="tk-var">$1</span>')
      .replace(/(^|[\s(;,{])(:\w+|rdfs?:\w+|owl:\w+|xsd:\w+)/g, '$1<span class="tk-term">$2</span>');
  }).join('');
}

export function CodeBlock({ code }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div className="code-block">
      <button type="button" className="code-copy" onClick={copy} aria-label="Copier la requête">
        <Copy size={13} aria-hidden="true" /> {copied ? 'Copié' : 'Copier'}
      </button>
      {/* eslint-disable-next-line react/no-danger */}
      <pre><code dangerouslySetInnerHTML={{ __html: highlightSparql(code) }} /></pre>
    </div>
  );
}

/** Panneau repliable listant les requêtes SPARQL exécutées pour produire la page. */
export function SparqlPanel({ items = [], defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  if (!items.length) return null;
  return (
    <section className={`sparql-panel ${open ? 'is-open' : ''}`}>
      <button type="button" className="sparql-toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <Code2 size={16} aria-hidden="true" />
        Requêtes SPARQL exécutées ({items.length})
        <ChevronDown size={16} className="chev" aria-hidden="true" />
      </button>
      {open && (
        <ol className="sparql-list">
          {items.map((it, i) => (
            <li key={i}>
              <p className="sparql-title">{i + 1}. {it.titre}</p>
              <CodeBlock code={it.requete} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

/* ---------- Tableau de résultats générique + export CSV ---------- */
function toCsv(columns, rows) {
  const esc = (v) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.join(';'), ...rows.map((r) => columns.map((c) => esc(r[c])).join(';'))].join('\n');
}

export function exportCsv(filename, columns, rows) {
  const blob = new Blob(['﻿' + toCsv(columns, rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const LINKABLE = { Molecule: '/molecules/', Medicament: '/medicaments/' };

export function ResultTable({ columns, rows, filename = 'resultats.csv', linkTypes = {} }) {
  const cols = columns && columns.length ? columns : rows.length ? Object.keys(rows[0]) : [];
  if (!rows.length) return <Empty>La requête ne renvoie aucun résultat.</Empty>;
  return (
    <div className="result">
      <div className="result-bar">
        <span>{rows.length} ligne{rows.length > 1 ? 's' : ''}</span>
        <button type="button" className="btn btn-compact" onClick={() => exportCsv(filename, cols, rows)}>
          <Download size={14} aria-hidden="true" /> Exporter CSV
        </button>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr>{cols.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {cols.map((c) => {
                  const v = r[c];
                  const base = linkTypes[c] && LINKABLE[linkTypes[c]];
                  const text = v === null || v === undefined ? '—' : typeof v === 'boolean' ? (v ? 'oui' : 'non') : String(v);
                  return <td key={c}>{base && v ? <Link to={base + v}>{text}</Link> : text}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ---------- Fenêtre modale accessible ---------- */
export function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const prev = document.activeElement;
    ref.current?.querySelector('input, select, textarea, button')?.focus();
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
      prev?.focus?.();
    };
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'is-wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby="modal-title" ref={ref}>
        <header className="modal-head">
          <h2 id="modal-title">{title}</h2>
          <button type="button" className="icon-btn" aria-label="Fermer" onClick={onClose}><X size={16} /></button>
        </header>
        {children}
      </div>
    </div>
  );
}

/* ---------- Sélection multiple par puces filtrables ---------- */
export function ChipSelect({ label, options, value, onChange, max }) {
  const [filter, setFilter] = useState('');
  const shown = useMemo(() => {
    const f = filter.toLowerCase();
    return options.filter((o) => !f || o.label.toLowerCase().includes(f) || o.id.toLowerCase().includes(f));
  }, [options, filter]);
  const toggle = (id) => {
    if (value.includes(id)) onChange(value.filter((v) => v !== id));
    else if (!max || value.length < max) onChange([...value, id]);
  };
  return (
    <fieldset className="chip-select">
      <legend>{label} {value.length > 0 && <span className="muted">({value.length})</span>}</legend>
      {options.length > 8 && (
        <input className="input input-sm" type="search" placeholder="Filtrer…" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label={`Filtrer ${label}`} />
      )}
      <div className="chips">
        {shown.map((o) => (
          <button key={o.id} type="button" className={`chip ${value.includes(o.id) ? 'is-active' : ''}`} aria-pressed={value.includes(o.id)} onClick={() => toggle(o.id)}>
            {o.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
