import {
  Network, Link2, BrainCircuit, UserRoundCheck, FlaskConical, Pill, Activity, ShieldAlert,
  HeartPulse, Users, ClipboardList, Syringe, UserRound, Stethoscope, Boxes, Waypoints,
} from 'lucide-react';

const icons = {
  Network, Link2, BrainCircuit, UserRoundCheck, FlaskConical, Pill, Activity, ShieldAlert,
  HeartPulse, Users, ClipboardList, Syringe, UserRound, Stethoscope, Boxes, Waypoints,
};

export default function Icon({ name, size = 20, ...rest }) {
  const Cmp = icons[name] || Boxes;
  return <Cmp size={size} strokeWidth={1.4} aria-hidden="true" {...rest} />;
}
