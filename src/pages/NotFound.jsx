import { Link } from 'react-router-dom';
import { PageHeader } from '../app/ui.jsx';

export default function NotFound() {
  return (
    <PageHeader eyebrow="Erreur 404" title="Page introuvable">
      <p>Cette adresse ne correspond à aucune page. <Link to="/molecules">Revenir aux molécules</Link>.</p>
    </PageHeader>
  );
}
