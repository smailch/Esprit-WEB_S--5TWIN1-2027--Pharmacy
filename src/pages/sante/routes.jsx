// Pages du module Pathologie + Personne, branchées dans src/App.jsx (sous AppShell).
import { Outlet, useParams, useSearchParams } from 'react-router-dom';
import AssistantSante from './AssistantSante';
import Graphe from './Graphe';
import PatientFiche from './PatientFiche';
import Personnes from './Personnes';
import './sante.css';

// Le style de ces pages est confiné sous .sante : il ne touche pas aux pages du module A.
export function SanteLayout() {
  return (
    <div className="sante">
      <Outlet />
      <p className="muted small disclaimer"><strong>Données fictives — aucun conseil médical.</strong></p>
    </div>
  );
}

export function PersonnesPage() {
  const [params] = useSearchParams();
  return <Personnes tab={params.get('tab') || 'patients'} />;
}

export function PatientPage() {
  const { id } = useParams();
  return <PatientFiche key={id} id={id} />;
}

export function GraphePage() {
  const { id } = useParams();
  return <Graphe id={id} />;
}

export function AssistantSantePage() {
  const [params] = useSearchParams();
  return <AssistantSante initial={params.get('q')} />;
}
