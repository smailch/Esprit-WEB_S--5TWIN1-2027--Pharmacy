import { useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Home from './pages/Home.jsx';
import AppShell from './app/AppShell.jsx';
import Molecules from './pages/Molecules.jsx';
import MoleculeDetail from './pages/MoleculeDetail.jsx';
import Medicaments from './pages/Medicaments.jsx';
import MedicamentDetail from './pages/MedicamentDetail.jsx';
import Comparateur from './pages/Comparateur.jsx';
import Interactions from './pages/Interactions.jsx';
import Assistant from './pages/Assistant.jsx';
import SparqlConsole from './pages/SparqlConsole.jsx';
import NotFound from './pages/NotFound.jsx';
import TableauSante from './pages/sante/TableauSante.jsx';
import Pathologies from './pages/sante/Pathologies.jsx';
import { AssistantSantePage, GraphePage, PatientPage, PersonnesPage, SanteLayout } from './pages/sante/routes.jsx';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route element={<AppShell />}>
          <Route path="/molecules" element={<Molecules />} />
          <Route path="/molecules/:id" element={<MoleculeDetail />} />
          <Route path="/medicaments" element={<Medicaments />} />
          <Route path="/medicaments/:id" element={<MedicamentDetail />} />
          <Route path="/comparateur" element={<Comparateur />} />
          <Route path="/interactions" element={<Interactions />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/sparql" element={<SparqlConsole />} />
          {/* Module Pathologie + Personne */}
          <Route element={<SanteLayout />}>
            <Route path="/sante" element={<TableauSante />} />
            <Route path="/pathologies" element={<Pathologies />} />
            <Route path="/personnes" element={<PersonnesPage />} />
            <Route path="/patients/:id" element={<PatientPage />} />
            <Route path="/assistant-sante" element={<AssistantSantePage />} />
            <Route path="/graphe" element={<GraphePage />} />
            <Route path="/graphe/:id" element={<GraphePage />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </>
  );
}
