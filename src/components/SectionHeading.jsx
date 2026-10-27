export default function SectionHeading({ label, title, children, light = false }) {
  return (
    <header className={`section-heading ${light ? 'is-light' : ''}`} data-reveal>
      {label && <p className="eyebrow">{label}</p>}
      <h2 className="display-title">{title}</h2>
      {children && <div className="section-intro">{children}</div>}
    </header>
  );
}
