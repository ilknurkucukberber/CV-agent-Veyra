import {
  AtsAnalysis,
  AtsCategoryKey,
  CATEGORY_LABELS,
  CATEGORY_WEIGHTS,
} from "@/types/ats";

function scoreColor(ratio: number): string {
  if (ratio >= 0.75) return "#16a34a"; // yeşil
  if (ratio >= 0.5) return "#d97706"; // amber
  return "#dc2626"; // kırmızı
}

function ScoreGauge({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const ratio = Math.max(0, Math.min(1, score / 100));
  const color = scoreColor(ratio);

  return (
    <div className="relative h-36 w-36 shrink-0" role="img" aria-label={`Toplam skor: ${score}/100`}>
      <svg viewBox="0 0 128 128" className="h-full w-full -rotate-90">
        <circle cx="64" cy="64" r={radius} fill="none" strokeWidth="12" className="stroke-gray-200 dark:stroke-gray-700" />
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          strokeWidth="12"
          strokeLinecap="round"
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - ratio)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold" style={{ color }}>
          {score}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">/ 100</span>
      </div>
    </div>
  );
}

function CategoryBars({ scores }: { scores: AtsAnalysis["category_scores"] }) {
  return (
    <div className="flex w-full flex-col gap-2">
      {(Object.keys(CATEGORY_WEIGHTS) as AtsCategoryKey[]).map((key) => {
        const value = scores[key] ?? 0;
        const max = CATEGORY_WEIGHTS[key];
        const ratio = max > 0 ? value / max : 0;
        return (
          <div key={key}>
            <div className="mb-0.5 flex items-baseline justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">{CATEGORY_LABELS[key]}</span>
              <span className="font-medium tabular-nums text-gray-900 dark:text-gray-100">
                {value}/{max}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${ratio * 100}%`, backgroundColor: scoreColor(ratio) }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AtsResultCard({ analysis }: { analysis: AtsAnalysis }) {
  return (
    <section className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        ATS Uyumluluk Değerlendirmesi
      </h2>

      <div className="mt-4 flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <ScoreGauge score={analysis.total_score} />
        <CategoryBars scores={analysis.category_scores} />
      </div>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
            Güçlü Yönler
          </h3>
          {analysis.strengths.length === 0 ? (
            <p className="text-sm text-gray-500">Belirgin bir güçlü yön tespit edilmedi.</p>
          ) : (
            <ul className="space-y-1.5">
              {analysis.strengths.map((item) => (
                <li key={item} className="flex gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <span aria-hidden className="mt-0.5 text-green-600">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-red-700 dark:text-red-400">
            Eksikler
          </h3>
          {analysis.gaps.length === 0 ? (
            <p className="text-sm text-gray-500">Önemli bir eksik tespit edilmedi.</p>
          ) : (
            <ul className="space-y-3">
              {analysis.gaps.map((gap) => (
                <li
                  key={gap.issue}
                  className="rounded-lg border border-red-100 bg-red-50 p-3 dark:border-red-900/40 dark:bg-red-950/30"
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {gap.issue}
                  </p>
                  <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-semibold">Neden önemli:</span> {gap.why_it_matters}
                  </p>
                  <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-semibold">Nasıl düzeltilir:</span> {gap.how_to_fix}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <p className="mt-6 rounded-lg bg-gray-50 p-3 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400">
        ⓘ {analysis.disclaimer}
      </p>
    </section>
  );
}
