export default function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`veyra-brand ${compact ? "veyra-brand-compact" : ""}`}>
      <svg className="veyra-mark" width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
        <rect x="1" y="1" width="38" height="38" rx="12" fill="#28243e" stroke="#63568a" />
        <path d="M10 12L19 29L30 11H24L19 20L15 12H10Z" fill="#d8ceff" />
        <circle cx="29" cy="28" r="2.5" fill="#e8c99a" />
      </svg>
      {!compact && <span className="veyra-wordmark"><b>veyra<span>✦</span></b><small>KARİYER ÇALIŞMA ALANI</small></span>}
    </span>
  );
}
