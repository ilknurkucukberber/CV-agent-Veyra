import { LinkedInOptimizeResult } from "@/types/linkedin";

export default function LinkedInResultCard({ result }: { result: LinkedInOptimizeResult }) {
  return (
    <section className="w-full max-w-2xl space-y-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        LinkedIn Profil Önerileri
      </h2>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
          Başlık Seçenekleri{" "}
          <span className="font-normal normal-case text-gray-400">
            (maks. {result.headline_max_length} karakter)
          </span>
        </h3>
        <ul className="space-y-2">
          {result.headline_options.map((headline) => (
            <li
              key={headline}
              className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            >
              {headline}
              <span
                className={`ml-2 text-xs ${
                  headline.length > result.headline_max_length
                    ? "text-red-600"
                    : "text-gray-400"
                }`}
              >
                {headline.length}/{result.headline_max_length}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
          Hakkında Bölümü
        </h3>
        <p className="whitespace-pre-wrap rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
          {result.about_section}
        </p>
      </div>

      {result.experience_descriptions.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
            Deneyim Açıklamaları
          </h3>
          <ul className="space-y-2">
            {result.experience_descriptions.map((exp) => (
              <li
                key={exp.role}
                className="rounded-lg border border-gray-200 p-3 dark:border-gray-700"
              >
                <p className="text-xs font-semibold text-gray-500">{exp.role}</p>
                <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                  {exp.linkedin_version}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
            Önerilen Beceriler
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {result.suggested_skills.map((skill) => (
              <span
                key={skill}
                className="rounded-full border border-green-300 bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-300">
            Profil Tamamlanma Listesi
          </h3>
          <ul className="space-y-1">
            {result.profile_completeness_checklist.map((item) => (
              <li key={item.item} className="flex items-center gap-2 text-sm">
                <span aria-hidden>
                  {item.present === true ? "✅" : item.present === false ? "❌" : "❔"}
                </span>
                <span className="text-gray-700 dark:text-gray-300">{item.item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
