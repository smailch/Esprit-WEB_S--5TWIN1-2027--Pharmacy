import Navbar from './components/Navbar.jsx';
import Hero from './components/Hero.jsx';
import ApproachSection from './components/ApproachSection.jsx';
import OntologyDiagram from './components/OntologyDiagram.jsx';
import RelationshipTable from './components/RelationshipTable.jsx';
import IndividualsSection from './components/IndividualsSection.jsx';
import OntoGraphSection from './components/OntoGraphSection.jsx';
import ValidationSection from './components/ValidationSection.jsx';
import TeamSection from './components/TeamSection.jsx';
import Footer from './components/Footer.jsx';
import { useReveal } from './hooks/useReveal.js';

export default function App() {
  useReveal();
  return (
    <>
      <a href="#contenu" className="skip-link">Aller au contenu</a>
      <Navbar />
      <main id="contenu">
        <Hero />
        <ApproachSection />
        <OntologyDiagram />
        <RelationshipTable />
        <IndividualsSection />
        <OntoGraphSection />
        <ValidationSection />
        <TeamSection />
      </main>
      <Footer />
    </>
  );
}
