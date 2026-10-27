import SectionHeading from './SectionHeading.jsx';
import ClassGrid from './ClassGrid.jsx';

export default function OntologyDiagram() {
  return (
    <section id="ontologie" className="section section-tint">
      <div className="container">
        <SectionHeading label="02 — MODÉLISATION" title="Une structure organisée de connaissances.">
          <p>
            Huit classes principales organisent le domaine pharmaceutique. Chaque classe se spécialise en sous-classes,
            puis s’incarne dans des individus concrets.
          </p>
        </SectionHeading>

        <div className="legend glass" data-reveal role="note" aria-label="Légende">
          <span className="legend-item"><span className="swatch swatch-class" />Classe</span>
          <span className="legend-item"><span className="swatch swatch-sub" />Sous-classe</span>
          <span className="legend-item"><span className="swatch swatch-ind" />Individu (instance)</span>
        </div>

        <ClassGrid />
      </div>
    </section>
  );
}
