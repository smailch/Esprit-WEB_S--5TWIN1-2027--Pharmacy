export default function Logo({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" className="logo-mark">
      <circle cx="16" cy="16" r="14.5" fill="none" stroke="currentColor" strokeWidth="0.9" opacity="0.55" />
      <circle cx="16" cy="16" r="10.5" fill="none" stroke="currentColor" strokeWidth="0.9" />
      <path d="M13.6 9h4.8v4.6H23v4.8h-4.6V23h-4.8v-4.6H9v-4.8h4.6z" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  );
}
