"use client";

import { useMemo, useState } from "react";
import {
  ChangeLogEntry,
  EditorVersion,
  ResumeContent,
} from "@/types/resume";
import VersionDiff from "./VersionDiff";

type Decision = "accepted" | "rejected";

const EDIT_LEVEL_LABELS: Record<string, string> = {
  light: "Hafif düzenleme",
  targeted: "Hedefli düzenleme",
  from_scratch: "Baştan oluşturma",
  manual: "Elle düzenleme",
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

/** İçerikteki tüm string alanlarda `search` -> `replace` uygular. */
function replaceInContent(content: ResumeContent, search: string, replace: string): ResumeContent {
  const walk = (value: unknown): unknown => {
    if (typeof value === "string") return value.includes(search) ? value.split(search).join(replace) : value;
    if (Array.isArray(value)) return value.map(walk);
    if (value && typeof value === "object") {
      return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, walk(v)]));
    }
    return value;
  };
  return walk(clone(content)) as ResumeContent;
}

/** Bir change_log kaydını içeriğe uygular (from -> to).

Önce düz string değişimi dener; bulunamazsa ve section `skills` gibi
string-listesi bir alanı işaret ediyorsa, hedef metni virgülle ayırıp
diziyi topluca günceller. */
function applyChange(
  content: ResumeContent,
  section: string,
  from: string,
  to: string,
): ResumeContent {
  const replaced = replaceInContent(content, from, to);
  if (JSON.stringify(replaced) !== JSON.stringify(content)) return replaced;

  const field = section.split("[")[0].split(".")[0];
  const draft = clone(content) as unknown as Record<string, unknown>;
  const value = draft[field];
  if (Array.isArray(value) && value.every((x) => typeof x === "string")) {
    draft[field] = to.split(",").map((s) => s.trim()).filter(Boolean);
    return draft as unknown as ResumeContent;
  }
  return content;
}

export default function CvEditor({ initialVersions }: { initialVersions: EditorVersion[] }) {
  const [versions, setVersions] = useState<EditorVersion[]>(initialVersions);
  const [activeId, setActiveId] = useState<number>(initialVersions[0]?.id ?? 0);
  const activeVersion = useMemo(
    () => versions.find((v) => v.id === activeId) ?? versions[0],
    [versions, activeId],
  );
  const [content, setContent] = useState<ResumeContent>(() => clone(activeVersion.content));
  const [decisions, setDecisions] = useState<Record<number, Decision>>({});
  const [dirty, setDirty] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [compareFromId, setCompareFromId] = useState<number | null>(null);

  const switchVersion = (id: number) => {
    const target = versions.find((v) => v.id === id);
    if (!target) return;
    setActiveId(id);
    setContent(clone(target.content));
    setDecisions({});
    setDirty(false);
  };

  const update = (updater: (draft: ResumeContent) => void) => {
    setContent((prev) => {
      const draft = clone(prev);
      updater(draft);
      return draft;
    });
    setDirty(true);
  };

  const decide = (index: number, entry: ChangeLogEntry, decision: Decision) => {
    if (decision === "rejected") {
      setContent((prev) => applyChange(prev, entry.section, entry.after, entry.before));
      setDirty(true);
    } else if (decisions[index] === "rejected") {
      // Reddedilmişti, tekrar kabul: before -> after geri uygula
      setContent((prev) => applyChange(prev, entry.section, entry.before, entry.after));
      setDirty(true);
    }
    setDecisions((prev) => ({ ...prev, [index]: decision }));
  };

  const saveAsNewVersion = () => {
    const nextNumber = Math.max(...versions.map((v) => v.version_number)) + 1;
    const newVersion: EditorVersion = {
      id: Math.max(...versions.map((v) => v.id)) + 1,
      version_number: nextNumber,
      edit_level: "manual",
      content: clone(content),
      change_log: [],
      created_at: new Date().toISOString(),
    };
    setVersions((prev) => [newVersion, ...prev]);
    setActiveId(newVersion.id);
    setDecisions({});
    setDirty(false);
  };

  return (
    <div className="grid min-h-screen grid-cols-1 gap-4 bg-gray-100 p-4 dark:bg-gray-950 lg:grid-cols-[220px_1fr_1fr]">
      {/* Versiyon geçmişi */}
      <aside className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
          Versiyon Geçmişi
        </h2>
        <ul className="space-y-1">
          {versions.map((v) => (
            <li key={v.id}>
              <button
                onClick={() => switchVersion(v.id)}
                className={`w-full rounded-lg px-2 py-1.5 text-left text-sm transition ${
                  v.id === activeId
                    ? "bg-blue-600 text-white"
                    : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                }`}
              >
                v{v.version_number} · {EDIT_LEVEL_LABELS[v.edit_level] ?? v.edit_level}
              </button>
            </li>
          ))}
        </ul>
        <button
          onClick={saveAsNewVersion}
          disabled={!dirty}
          className="mt-3 w-full rounded-lg bg-green-600 px-2 py-1.5 text-sm font-medium text-white transition enabled:hover:bg-green-700 disabled:opacity-40"
        >
          Yeni versiyon olarak kaydet
        </button>

        {versions.length > 1 && (
          <div className="mt-4 border-t border-gray-200 pt-3 dark:border-gray-700">
            <button
              onClick={() => {
                if (!compareMode) {
                  const fallback = versions.find((v) => v.id !== activeId);
                  setCompareFromId(fallback?.id ?? null);
                }
                setCompareMode((prev) => !prev);
              }}
              className={`w-full rounded-lg px-2 py-1.5 text-sm font-medium transition ${
                compareMode
                  ? "bg-gray-700 text-white hover:bg-gray-800"
                  : "border border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              }`}
            >
              {compareMode ? "Karşılaştırmayı kapat" : "İki versiyonu karşılaştır"}
            </button>
          </div>
        )}
      </aside>

      {compareMode && compareFromId !== null ? (
        <section className="col-span-1 space-y-3 overflow-y-auto rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900 lg:col-span-2">
          <div className="flex flex-wrap items-center gap-3 border-b border-gray-200 pb-3 dark:border-gray-700">
            <label className="text-sm text-gray-600 dark:text-gray-400">
              Eski:{" "}
              <select
                value={compareFromId}
                onChange={(e) => setCompareFromId(Number(e.target.value))}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>v{v.version_number}</option>
                ))}
              </select>
            </label>
            <label className="text-sm text-gray-600 dark:text-gray-400">
              Yeni:{" "}
              <select
                value={activeId}
                onChange={(e) => setActiveId(Number(e.target.value))}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>v{v.version_number}</option>
                ))}
              </select>
            </label>
          </div>
          {(() => {
            const fromVersion = versions.find((v) => v.id === compareFromId);
            const toVersion = versions.find((v) => v.id === activeId);
            if (!fromVersion || !toVersion) return null;
            return <VersionDiff a={fromVersion} b={toVersion} />;
          })()}
        </section>
      ) : (
      <>
      {/* Sol: düzenlenebilir alanlar + öneriler */}
      <section className="space-y-4 overflow-y-auto rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Düzenle</h2>

        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold text-gray-900 dark:text-gray-100">Kişisel Bilgiler</legend>
          {(["name", "email", "phone"] as const).map((field) => (
            <input
              key={field}
              value={content.personal_info[field] ?? ""}
              placeholder={{ name: "Ad Soyad", email: "E-posta", phone: "Telefon" }[field]}
              onChange={(e) =>
                update((d) => {
                  d.personal_info[field] = e.target.value || null;
                })
              }
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          ))}
        </fieldset>

        <fieldset>
          <legend className="mb-1 text-sm font-semibold text-gray-900 dark:text-gray-100">Profesyonel Özet</legend>
          <textarea
            value={content.summary ?? ""}
            rows={3}
            placeholder="(from_scratch modunda üretilir)"
            onChange={(e) =>
              update((d) => {
                d.summary = e.target.value || null;
              })
            }
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-gray-900 dark:text-gray-100">Deneyim</legend>
          {content.experience.map((exp, i) => (
            <div key={i} className="rounded-lg border border-gray-200 p-2 dark:border-gray-700">
              <div className="mb-1 text-xs font-medium text-gray-500">
                {exp.role} — {exp.company}
              </div>
              <textarea
                value={exp.description}
                rows={3}
                onChange={(e) =>
                  update((d) => {
                    d.experience[i].description = e.target.value;
                  })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
          ))}
        </fieldset>

        <fieldset>
          <legend className="mb-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
            Beceriler <span className="font-normal text-gray-400">(virgülle ayırın)</span>
          </legend>
          <input
            value={content.skills.join(", ")}
            onChange={(e) =>
              update((d) => {
                d.skills = e.target.value.split(",").map((s) => s.trim()).filter(Boolean);
              })
            }
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </fieldset>

        {/* Öneriler */}
        {activeVersion.change_log.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Öneriler ({activeVersion.change_log.length})
            </h3>
            <ul className="space-y-2">
              {activeVersion.change_log.map((entry, i) => {
                const decision = decisions[i];
                return (
                  <li
                    key={i}
                    className={`rounded-lg border p-3 text-sm ${
                      decision === "accepted"
                        ? "border-green-300 bg-green-50 dark:border-green-800 dark:bg-green-950/30"
                        : decision === "rejected"
                          ? "border-gray-200 bg-gray-50 opacity-60 dark:border-gray-700 dark:bg-gray-800"
                          : "border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/30"
                    }`}
                  >
                    <div className="text-xs font-medium text-gray-500">{entry.section}</div>
                    {entry.before && (
                      <p className="mt-1 text-xs text-red-700 line-through dark:text-red-400">
                        {entry.before}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-green-700 dark:text-green-400">{entry.after}</p>
                    <p className="mt-1 text-xs italic text-gray-600 dark:text-gray-400">
                      {entry.reason}
                    </p>
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => decide(i, entry, "accepted")}
                        disabled={decision === "accepted"}
                        className="rounded-md bg-green-600 px-2 py-1 text-xs font-medium text-white transition enabled:hover:bg-green-700 disabled:opacity-50"
                      >
                        Kabul et
                      </button>
                      <button
                        onClick={() => decide(i, entry, "rejected")}
                        disabled={decision === "rejected"}
                        className="rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white transition enabled:hover:bg-red-700 disabled:opacity-50"
                      >
                        Reddet
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>

      {/* Sağ: canlı önizleme */}
      <section className="overflow-y-auto rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Önizleme</h2>
        <div className="mx-auto max-w-xl rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-950">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {content.personal_info.name ?? "İsimsiz"}
          </h1>
          <p className="text-sm text-gray-500">
            {[content.personal_info.email, content.personal_info.phone]
              .filter(Boolean)
              .join(" · ")}
          </p>

          {content.summary && (
            <PreviewSection title="Profesyonel Özet">
              <p className="text-sm text-gray-700 dark:text-gray-300">{content.summary}</p>
            </PreviewSection>
          )}

          {content.experience.length > 0 && (
            <PreviewSection title="Deneyim">
              {content.experience.map((exp, i) => (
                <div key={i} className="mb-2">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {exp.role} · {exp.company}
                    <span className="ml-2 font-normal text-gray-400">
                      {[exp.start_date, exp.end_date ?? "Halen"].filter(Boolean).join(" – ")}
                    </span>
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{exp.description}</p>
                </div>
              ))}
            </PreviewSection>
          )}

          {content.education.length > 0 && (
            <PreviewSection title="Eğitim">
              {content.education.map((edu, i) => (
                <p key={i} className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="font-semibold">{edu.school}</span> — {edu.department}
                  {edu.gpa ? ` (GPA: ${edu.gpa})` : ""}
                  <span className="ml-2 text-gray-400">
                    {[edu.start_date, edu.end_date].filter(Boolean).join(" – ")}
                  </span>
                </p>
              ))}
            </PreviewSection>
          )}

          {content.projects.length > 0 && (
            <PreviewSection title="Projeler">
              {content.projects.map((p, i) => (
                <p key={i} className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="font-semibold">{p.name}:</span> {p.description}
                  {p.technologies.length > 0 && (
                    <span className="text-gray-400"> ({p.technologies.join(", ")})</span>
                  )}
                </p>
              ))}
            </PreviewSection>
          )}

          {content.skills.length > 0 && (
            <PreviewSection title="Beceriler">
              <div className="flex flex-wrap gap-1.5">
                {content.skills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </PreviewSection>
          )}

          {content.certificates.length > 0 && (
            <PreviewSection title="Sertifikalar">
              {content.certificates.map((c) => (
                <p key={c} className="text-sm text-gray-700 dark:text-gray-300">{c}</p>
              ))}
            </PreviewSection>
          )}

          {content.languages.length > 0 && (
            <PreviewSection title="Diller">
              {content.languages.map((l, i) => (
                <p key={i} className="text-sm text-gray-700 dark:text-gray-300">
                  {l.language}
                  {l.level ? ` — ${l.level}` : ""}
                </p>
              ))}
            </PreviewSection>
          )}
        </div>
      </section>
      </>
      )}
    </div>
  );
}

function PreviewSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <h3 className="mb-1 border-b border-gray-200 pb-0.5 text-xs font-bold uppercase tracking-wider text-gray-500 dark:border-gray-700">
        {title}
      </h3>
      {children}
    </div>
  );
}
