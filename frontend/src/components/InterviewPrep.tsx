"use client";

import { useMemo, useState } from "react";
import {
  InterviewQuestion,
  InterviewSession,
  QuestionSource,
  SESSION_TYPE_LABELS,
  SOURCE_LABELS,
} from "@/types/interview";
import { apiFetch } from "@/lib/api";

const STAR_FIELDS = [
  { key: "situation", label: "Durum (Situation)", hint: "Bağlam neydi?" },
  { key: "task", label: "Görev (Task)", hint: "Senin sorumluluğun neydi?" },
  { key: "action", label: "Eylem (Action)", hint: "Ne yaptın?" },
  { key: "result", label: "Sonuç (Result)", hint: "Sonuç ne oldu?" },
] as const;

type StarKey = (typeof STAR_FIELDS)[number]["key"];
type StarNote = Record<StarKey, string>;

const EMPTY_STAR: StarNote = { situation: "", task: "", action: "", result: "" };

const SOURCE_STYLES: Record<QuestionSource, string> = {
  general: "border-gray-300 bg-gray-100 text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300",
  cv_specific: "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300",
  job_specific: "border-teal-300 bg-teal-50 text-teal-800 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-300",
};

/** STAR notunu tek bir metne serileştirir (backend `answer` alanına yazılır). */
function serializeStar(note: StarNote): string {
  const filled = STAR_FIELDS.filter((f) => note[f.key].trim());
  if (filled.length === 0) return "";
  return filled.map((f) => `${f.label}: ${note[f.key].trim()}`).join("\n");
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function parseStar(answer: string | null): StarNote {
  if (!answer) return { ...EMPTY_STAR };
  const note = { ...EMPTY_STAR };
  for (const field of STAR_FIELDS) {
    // Etiketler parantez içeriyor ("Durum (Situation)") — regex'e kaçırılmalı
    const match = answer.match(new RegExp(`${escapeRegex(field.label)}:\\s*(.*)`));
    if (match) note[field.key] = match[1].trim();
  }
  // STAR formatında değilse ham metni ilk alana koy
  if (STAR_FIELDS.every((f) => !note[f.key])) note.situation = answer;
  return note;
}

function QuestionCard({
  question,
  sessionId,
}: {
  question: InterviewQuestion;
  sessionId: number;
}) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState<StarNote>(() => parseStar(question.answer));
  const [saved, setSaved] = useState(Boolean(question.answer));
  const [saving, setSaving] = useState(false);

  const plainAnswer = !question.star_applicable;

  const save = async () => {
    const payload = plainAnswer ? note.situation : serializeStar(note);
    setSaving(true);
    try {
      await apiFetch(`/interview/sessions/${sessionId}/questions/${question.id}`, {
        method: "PATCH",
        body: JSON.stringify({ answer: payload || null }),
      });
      setSaved(Boolean(payload.trim()));
    } finally {
      setSaving(false);
    }
  };

  const source = question.source ?? "general";

  return (
    <li className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full border px-2 py-0.5 text-xs font-medium ${SOURCE_STYLES[source]}`}
        >
          {SOURCE_LABELS[source]}
        </span>
        {question.category && (
          <span className="text-xs text-gray-500">{question.category}</span>
        )}
        {question.star_applicable && (
          <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            ★ STAR
          </span>
        )}
        {saved && (
          <span className="ml-auto text-xs font-medium text-green-600 dark:text-green-400">
            ✓ Not kaydedildi
          </span>
        )}
      </div>

      <p className="mt-2 text-sm text-gray-900 dark:text-gray-100">{question.question}</p>

      <button
        onClick={() => setOpen((v) => !v)}
        className="mt-3 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-blue-700"
      >
        {open
          ? "Notu gizle"
          : question.star_applicable
            ? "STAR ile cevapla"
            : "Not al"}
      </button>

      {open && (
        <div className="mt-3 space-y-2">
          {plainAnswer ? (
            <textarea
              rows={4}
              value={note.situation}
              onChange={(e) => setNote({ ...note, situation: e.target.value })}
              placeholder="Cevap taslağınız…"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          ) : (
            STAR_FIELDS.map((field) => (
              <div key={field.key}>
                <label className="mb-0.5 block text-xs font-semibold text-gray-700 dark:text-gray-300">
                  {field.label}
                </label>
                <textarea
                  rows={2}
                  value={note[field.key]}
                  onChange={(e) => setNote({ ...note, [field.key]: e.target.value })}
                  placeholder={field.hint}
                  className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                />
              </div>
            ))
          )}
          <button
            onClick={save}
            disabled={saving}
            className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white transition enabled:hover:bg-green-700 disabled:opacity-50"
          >
            {saving ? "Kaydediliyor…" : "Notu kaydet"}
          </button>
        </div>
      )}
    </li>
  );
}

export default function InterviewPrep({ session }: { session: InterviewSession }) {
  const [sourceFilter, setSourceFilter] = useState<QuestionSource | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const categories = useMemo(
    () =>
      Array.from(
        new Set(session.questions.map((q) => q.category).filter(Boolean) as string[]),
      ).sort(),
    [session.questions],
  );

  const visible = useMemo(
    () =>
      session.questions.filter(
        (q) =>
          (sourceFilter === "all" || q.source === sourceFilter) &&
          (categoryFilter === "all" || q.category === categoryFilter),
      ),
    [session.questions, sourceFilter, categoryFilter],
  );

  const counts = useMemo(() => {
    const base: Record<string, number> = { all: session.questions.length };
    for (const q of session.questions) {
      const key = q.source ?? "general";
      base[key] = (base[key] ?? 0) + 1;
    }
    return base;
  }, [session.questions]);

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4">
      <header className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Mülakat Hazırlığı
        </p>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {SESSION_TYPE_LABELS[session.session_type] ?? session.session_type}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {session.questions.length} soru ·{" "}
          {session.job_posting_id ? "İlana göre hazırlandı" : "CV'nize göre hazırlandı"}
        </p>

        <div className="mt-4 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {(["all", "general", "cv_specific", "job_specific"] as const).map((key) => (
              <button
                key={key}
                onClick={() => setSourceFilter(key)}
                disabled={key !== "all" && !counts[key]}
                className={`rounded-full px-3 py-1 text-xs font-medium transition disabled:opacity-30 ${
                  sourceFilter === key
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                }`}
              >
                {key === "all" ? "Tümü" : SOURCE_LABELS[key]} ({counts[key] ?? 0})
              </button>
            ))}
          </div>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            aria-label="Kategoriye göre filtrele"
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:w-auto"
          >
            <option value="all">Tüm kategoriler</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>
      </header>

      {visible.length === 0 ? (
        <p className="rounded-xl border border-gray-200 bg-white p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
          Bu filtreye uyan soru yok.
        </p>
      ) : (
        <ul className="space-y-3">
          {visible.map((question) => (
            <QuestionCard key={question.id} question={question} sessionId={session.id} />
          ))}
        </ul>
      )}
    </div>
  );
}
