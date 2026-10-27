// Données de l'ontologie « Ontologie Pharmaceutique et Santé » (NeoCoders · 5 TWIN · 2026–2027).
// Toutes les valeurs reprennent la présentation académique ; aucune donnée médicale réelle.

export const HERO_VIDEO_SRC = '/videos/pharmacy-hero.mp4';
export const HERO_POSTER_SRC = '/videos/pharmacy-hero-poster.png';

export const navLinks = [
  { id: 'accueil', label: 'Accueil' },
  { id: 'approche', label: 'Notre approche' },
  { id: 'ontologie', label: 'Ontologie' },
  { id: 'relations', label: 'Relations' },
  { id: 'individus', label: 'Individus' },
  { id: 'ontographe', label: 'Ontographe' },
];

export const heroMetrics = [
  { value: '8', label: 'classes principales' },
  { value: '5', label: 'relations clés présentées' },
  { value: 'HermiT', label: 'raisonnement logique' },
];

export const approachCards = [
  {
    icon: 'Network',
    title: 'Interopérabilité',
    text: 'Un vocabulaire commun pour structurer et relier les connaissances issues de différentes sources.',
  },
  {
    icon: 'Link2',
    title: 'Liens explicites',
    text: 'Relier les substances actives aux effets secondaires, aux contre-indications et aux pathologies concernées.',
  },
  {
    icon: 'BrainCircuit',
    title: 'Raisonnement logique',
    text: 'Utiliser le raisonneur HermiT pour détecter les incohérences dans l’ontologie.',
  },
  {
    icon: 'UserRoundCheck',
    title: 'Données fictives',
    text: 'Utiliser des individus de démonstration, notamment des patients anonymisés fictifs comme Patient_F001.',
  },
];

// Les 8 classes principales et leurs sous-classes.
export const ontologyClasses = [
  {
    id: 'SubstanceActive',
    icon: 'FlaskConical',
    summary: 'Le principe actif responsable de l’effet du médicament.',
    detail: 'Classée selon sa famille thérapeutique. Elle est reliée aux effets secondaires et aux contre-indications.',
    subclasses: [{ name: 'Analgésique' }, { name: 'Antibiotique' }, { name: 'AntiInflammatoire' }, { name: 'Antidiabétique' }],
  },
  {
    id: 'Médicament',
    icon: 'Pill',
    summary: 'Le produit pharmaceutique commercialisé.',
    detail: 'Un médicament contient un ou plusieurs principes actifs et est indiqué pour des pathologies.',
    subclasses: [{ name: 'Princeps' }, { name: 'Générique' }],
  },
  {
    id: 'EffetSecondaire',
    icon: 'Activity',
    summary: 'Un effet indésirable pouvant être provoqué par une substance.',
    detail: 'Distingué selon son niveau de gravité.',
    subclasses: [{ name: 'EffetLéger' }, { name: 'EffetGrave' }],
  },
  {
    id: 'ContreIndication',
    icon: 'ShieldAlert',
    summary: 'Une situation dans laquelle une substance ne doit pas, ou doit prudemment, être utilisée.',
    detail: 'Une contre-indication concerne une pathologie donnée.',
    subclasses: [{ name: 'Absolue' }, { name: 'Relative' }],
  },
  {
    id: 'Pathologie',
    icon: 'HeartPulse',
    summary: 'La maladie ou l’affection concernée.',
    detail: 'Cible des indications des médicaments et objet des contre-indications.',
    subclasses: [{ name: 'MaladieAiguë' }, { name: 'MaladieChronique' }],
  },
  {
    id: 'Personne',
    icon: 'Users',
    summary: 'Les acteurs : patients et professionnels de santé.',
    detail: 'Le patient se décline en adulte ou pédiatrique ; les professionnels sont le médecin et le pharmacien.',
    subclasses: [
      { name: 'Patient', children: ['Adulte', 'Pédiatrique'] },
      { name: 'Médecin' },
      { name: 'Pharmacien' },
    ],
  },
  {
    id: 'Prescription',
    icon: 'ClipboardList',
    summary: 'L’acte reliant un patient à un ou plusieurs médicaments.',
    detail: 'Elle peut être simple ou renouvelable.',
    subclasses: [{ name: 'PrescriptionSimple' }, { name: 'PrescriptionRenouvelable' }],
  },
  {
    id: 'ModalitéAdministration',
    icon: 'Syringe',
    summary: 'La manière dont le médicament est présenté et administré.',
    detail: 'Elle couvre la forme galénique et la voie d’administration.',
    subclasses: [{ name: 'FormeGalénique' }, { name: 'VoieAdministration' }],
  },
];

// Les 5 relations principales présentées.
export const relations = [
  {
    name: 'contientPrincipeActif',
    domain: 'Médicament',
    range: 'SubstanceActive',
    sentence: 'Un médicament contient une substance active — par exemple, Advil contient de l’Ibuprofène.',
  },
  {
    name: 'peutProvoquer',
    domain: 'SubstanceActive',
    range: 'EffetSecondaire',
    sentence: 'Une substance active peut provoquer un effet secondaire, léger ou grave.',
  },
  {
    name: 'aPourContreIndication',
    domain: 'SubstanceActive',
    range: 'ContreIndication',
    sentence: 'Une substance active est associée à une ou plusieurs contre-indications.',
  },
  {
    name: 'concernePathologie',
    domain: 'ContreIndication',
    range: 'Pathologie',
    sentence: 'Une contre-indication concerne une pathologie — par exemple, CI_Ulcère_Gastrique concerne Ulcère_Gastrique.',
  },
  {
    name: 'estIndiquéPour',
    domain: 'Médicament',
    range: 'Pathologie',
    sentence: 'Un médicament est indiqué pour une pathologie — par exemple, Doliprane pour la Fièvre.',
  },
];

export const datatypeProperties = {
  total: 11,
  examples: ['nomCommercial', 'codeATC', 'dosage', 'gravitéEffet', 'datePrescription', 'spécialité'],
};

// Individus de démonstration (exemples présentés).
export const individualGroups = [
  { cls: 'SubstanceActive', label: 'Substances actives', icon: 'FlaskConical', items: ['Paracétamol', 'Ibuprofène', 'Amoxicilline'] },
  { cls: 'Médicament', label: 'Médicaments', icon: 'Pill', items: ['Doliprane', 'Advil', 'Augmentin'] },
  { cls: 'EffetSecondaire', label: 'Effets secondaires', icon: 'Activity', items: ['Nausée', 'Hémorragie_Digestive'] },
  { cls: 'ContreIndication', label: 'Contre-indications', icon: 'ShieldAlert', items: ['CI_Ulcère_Gastrique'] },
  { cls: 'Pathologie', label: 'Pathologies', icon: 'HeartPulse', items: ['Fièvre', 'Diabète_Type2', 'Ulcère_Gastrique'] },
  { cls: 'Patient', label: 'Patients fictifs', icon: 'UserRound', items: ['Patient_F001', 'Patient_F002', 'Patient_F003'] },
  { cls: 'Personne', label: 'Professionnels fictifs', icon: 'Stethoscope', items: ['Dr_Fictif_01', 'Pharmacien_Fictif_01'] },
  { cls: 'Prescription', label: 'Prescriptions', icon: 'ClipboardList', items: ['Presc_001', 'Presc_002', 'Presc_003'] },
  { cls: 'ModalitéAdministration', label: 'Modalités', icon: 'Syringe', items: ['Comprimé', 'Gélule', 'Voie_Orale'] },
];

export const exampleFlow = [
  { name: 'Patient_F001', type: 'Patient' },
  { name: 'Presc_001', type: 'Prescription' },
  { name: 'Advil', type: 'Médicament' },
  { name: 'Ibuprofène', type: 'SubstanceActive' },
];

// Ontographe : nœuds et arêtes limités aux relations de la présentation.
export const graphNodes = [
  { id: 'Patient', x: 90, y: 90, kind: 'class' },
  { id: 'Prescription', x: 300, y: 90, kind: 'class' },
  { id: 'Médicament', x: 510, y: 90, kind: 'class' },
  { id: 'SubstanceActive', x: 510, y: 300, kind: 'class' },
  { id: 'Pathologie', x: 800, y: 90, kind: 'class' },
  { id: 'EffetSecondaire', x: 260, y: 470, kind: 'class' },
  { id: 'ContreIndication', x: 800, y: 470, kind: 'class' },
  { id: 'Advil', x: 400, y: 200, kind: 'individual', of: 'Médicament' },
  { id: 'Ibuprofène', x: 720, y: 220, kind: 'individual', of: 'SubstanceActive' },
];

export const graphEdges = [
  { from: 'Médicament', to: 'SubstanceActive', label: 'contientPrincipeActif' },
  { from: 'SubstanceActive', to: 'EffetSecondaire', label: 'peutProvoquer' },
  { from: 'SubstanceActive', to: 'ContreIndication', label: 'aPourContreIndication' },
  { from: 'ContreIndication', to: 'Pathologie', label: 'concernePathologie' },
  { from: 'Médicament', to: 'Pathologie', label: 'estIndiquéPour' },
  // Liens illustratifs de l'exemple Patient_F001 → Presc_001 → Advil (propriétés liées aux prescriptions de l'ontologie complète).
  { from: 'Patient', to: 'Prescription', label: 'prescription', dashed: true },
  { from: 'Prescription', to: 'Médicament', label: 'médicament prescrit', dashed: true },
  { from: 'Advil', to: 'Médicament', label: 'instance de', type: true },
  { from: 'Ibuprofène', to: 'SubstanceActive', label: 'instance de', type: true },
  { from: 'Advil', to: 'Ibuprofène', label: 'contientPrincipeActif' },
];

export const validationSteps = [
  { icon: 'Boxes', title: 'Modélisation', text: 'Définir les classes, sous-classes, propriétés et individus dans l’ontologie.' },
  { icon: 'BrainCircuit', title: 'Raisonnement', text: 'Utiliser HermiT pour vérifier la cohérence logique selon les axiomes définis.' },
  { icon: 'Waypoints', title: 'Visualisation', text: 'Explorer les connexions à travers OntoGraf et la représentation interactive du site.' },
];

export const team = ['Allaya Ahmed', 'Gobji Walid', 'Missaoui Mourad', 'Chemlali Ismail'];
