"use client";

import { EditorVersion, ResumeContent } from "@/types/resume";

const EDIT_LEVEL_LABELS: Record<string, string> = {
  light: "Hafif düzenleme",
  targeted: "Hedefli düzenleme",
  from_scratch: "Baştan oluşturma",
  manual: "Elle düzenleme",
};

function FieldDiff({ label, before, after }: { label: string; before: string; after: string }) {
  const changed = before !== after;
  return (
    <div className={`rounded-lg border p-2.5 text-sm ${changed ? "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/20" : "border-gray-200 dark:border-gray-700"}`}>
      <div className="mb-1 text-xs font-medium text-gray-500">{label}</div>
      {changed && before && (
        <p className="text-red-700 line-through dark:text-red-400">{before}</p>
      )}
      <p className={changed ? "text-green-700 dark:text-green-400" : "text-gray-700 dark:text-gray-300"}>
        {after || "—"}
      </p>
    </div>
  );
}

function ListDiff({ label, before, after }: { label: string; before: string[]; after: string[] }) {
  const removed = before.filter((item) => !after.includes(item));
  const added = after.filter((item) => !before.includes(item));
  const kept = after.filter((item) => before.includes(item));
  const changed = removed.length > 0 || added.length > 0;

  return (
    <div className={`rounded-lg border p-2.5 text-sm ${changed ? "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/20" : "border-gray-200 dark:border-gray-700"}`}>
      <div className="mb-1.5 text-xs font-medium text-gray-500">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {kept.map((item) => (
          <span key={`kept-${item}`} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
            {item}
          </span>
        ))}
        {removed.map((item) => (
          <span key={`removed-${item}`} className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700 line-through dark:bg-red-950/40 dark:text-red-400">
            {item}
          </span>
        ))}
        {added.map((item) => (
          <span key={`added-${item}`} className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950/40 dark:text-green-400">
            {item}
          </span>
        ))}
        {kept.length === 0 && removed.length === 0 && added.length === 0 && (
          <span className="text-xs text-gray-400">—</span>
        )}
      </div>
    </div>
  );
}

function experienceKey(exp: ResumeContent["experience"][number]): string {
  return `${exp.company}::${exp.role}`;
}

export default function VersionDiff({ a, b }: { a: EditorVersion; b: EditorVersion }) {
  const before = a.content;
  const after = b.content;

  const beforeExpByKey = new Map(before.experience.map((e) => [experienceKey(e), e]));
  const afterExpByKey = new Map(after.experience.map((e) => [experienceKey(e), e]));
  const experienceKeys = Array.from(new Set([...beforeExpByKey.keys(), ...afterExpByKey.keys()]));

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-gray-200 px-2.5 py-1 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
            v{a.version_number} · {EDIT_LEVEL_LABELS[a.edit_level] ?? a.edit_level}
          </span>
          <span className="text-gray-400">→</span>
          <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-400">
            v{b.version_number} · {EDIT_LEVEL_LABELS[b.edit_level] ?? b.edit_level}
          </span>
        </div>
        <p className="text-xs text-gray-500">
          <span className="text-red-600 line-through dark:text-red-400">Eski</span>
          {" / "}
          <span className="text-green-600 dark:text-green-400">Yeni</span>
        </p>
      </header>

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Kişisel Bilgiler</h3>
        <FieldDiff label="Ad Soyad" before={before.personal_info.name ?? ""} after={after.personal_info.name ?? ""} />
        <FieldDiff label="E-posta" before={before.personal_info.email ?? ""} after={after.personal_info.email ?? ""} />
        <FieldDiff label="Telefon" before={before.personal_info.phone ?? ""} after={after.personal_info.phone ?? ""} />
      </section>

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Profesyonel Özet</h3>
        <FieldDiff label="Özet" before={before.summary ?? ""} after={after.summary ?? ""} />
      </section>

      {experienceKeys.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Deneyim</h3>
          {experienceKeys.map((key) => {
            const afterExp = afterExpByKey.get(key);
            const beforeExp = beforeExpByKey.get(key);
            const label = afterExp
              ? `${afterExp.role} — ${afterExp.company}`
              : `${beforeExp?.role} — ${beforeExp?.company} (kaldırıldı)`;
            return (
              <FieldDiff
                key={key}
                label={label}
                before={beforeExp?.description ?? ""}
                after={afterExp?.description ?? ""}
              />
            );
          })}
        </section>
      )}

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Beceriler</h3>
        <ListDiff label="Beceriler" before={before.skills} after={after.skills} />
      </section>

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Sertifikalar</h3>
        <ListDiff label="Sertifikalar" before={before.certificates} after={after.certificates} />
      </section>

      {b.change_log.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            v{b.version_number} için AI değişiklik gerekçeleri
          </h3>
          <ul className="space-y-2">
            {b.change_log.map((entry, i) => (
              <li key={i} className="rounded-lg border border-gray-200 p-2.5 text-sm dark:border-gray-700">
                <span className="text-xs font-medium text-gray-500">{entry.section}</span>
                <p className="mt-1 italic text-gray-600 dark:text-gray-400">{entry.reason}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
