import { JobMatch, JobPosting } from "@/types/job";

function matchColor(pct: number): string {
  if (pct >= 75) return "#16a34a";
  if (pct >= 50) return "#d97706";
  return "#dc2626";
}

function matchLabel(pct: number): string {
  if (pct >= 75) return "Güçlü eşleşme";
  if (pct >= 50) return "Kısmi eşleşme";
  return "Zayıf eşleşme";
}

function MatchMeter({ percentage }: { percentage: number }) {
  const color = matchColor(percentage);
  return (
    <div className="w-full">
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-sm text-gray-600 dark:text-gray-400">{matchLabel(percentage)}</span>
        <span className="text-2xl font-bold tabular-nums" style={{ color }}>
          %{percentage}
        </span>
      </div>
      <div
        className="h-3 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
        role="meter"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Eşleşme oranı"
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function SkillBadges({
  skills,
  variant,
}: {
  skills: string[];
  variant: "matched" | "missing";
}) {
  const styles =
    variant === "matched"
      ? "border-green-300 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300"
      : "border-red-300 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300";

  if (skills.length === 0) {
    return <p className="text-sm text-gray-500">—</p>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <span
          key={skill}
          className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles}`}
        >
          {variant === "matched" ? "✓" : "✗"} {skill}
        </span>
      ))}
    </div>
  );
}

export default function JobMatchCard({
  match,
  posting,
}: {
  match: JobMatch;
  posting?: JobPosting;
}) {
  return (
    <section className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {posting?.title ?? "İlan Eşleşmesi"}
        </h2>
        {posting && (
          <p className="text-sm text-gray-500">
            {[posting.company, posting.location].filter(Boolean).join(" · ")}
          </p>
        )}
      </header>

      <MatchMeter percentage={match.match_percentage} />

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
            Eşleşen Beceriler ({match.matched_skills.length})
          </h3>
          <SkillBadges skills={match.matched_skills} variant="matched" />
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-red-700 dark:text-red-400">
            Eksik Beceriler ({match.missing_skills.length})
          </h3>
          <SkillBadges skills={match.missing_skills} variant="missing" />
        </div>
      </div>

      {match.improvement_suggestions.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
            Öneriler
          </h3>
          <ul className="space-y-2">
            {match.improvement_suggestions.map((s) => (
              <li
                key={s.suggestion}
                className="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-900 dark:bg-blue-950/30"
              >
                <p className="text-sm text-gray-900 dark:text-gray-100">{s.suggestion}</p>
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{s.reason}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-6 rounded-lg bg-gray-50 p-3 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400">
        ⓘ Bu eşleşme oranı uygulamanın kendi tahmini değerlendirmesidir; işverenin
        değerlendirme sonucunu yansıtmaz.
      </p>
    </section>
  );
}
