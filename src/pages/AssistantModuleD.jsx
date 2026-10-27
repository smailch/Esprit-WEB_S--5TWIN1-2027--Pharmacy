import { PageHeader } from '../app/ui.jsx';
import AssistantPrescriptions from '../app/AssistantPrescriptions.jsx';
import '../app/moduleD.css';

export default function AssistantModuleD() {
  return (
    <>
      <PageHeader eyebrow="Module D · API IA PrescriNLU-D" title="Assistant prescriptions et données cliniques" />
      <AssistantPrescriptions />
    </>
  );
}
