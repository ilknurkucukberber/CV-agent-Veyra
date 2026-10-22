"use client";

import { useMemo, useState } from "react";
import { CareerRoadmap as Roadmap } from "@/types/roadmap";
import { apiFetch } from "@/lib/api";

export default function CareerRoadmapView({ roadmap }: { roadmap: Roadmap }) {
  const [completed, setCompleted] = useState<number[]>(roadmap.completed_steps);
  const [saving, setSaving] = useState(false);

  const total = roadmap.development_plan.length;
  const progress = useMemo(
    () => (total === 0 ? 0 : Math.round((completed.length / total) * 100)),
    [completed.length, total],
  );

  const toggle = async (step: number) => {
    const next = completed.includes(step)
      ? completed.filter((s) => s !== step)
      : [...completed, step].sort((a, b) => a - b);
    setCompleted(next);

    setSaving(true);
    try {
      await apiFetch(`/career-roadmap/${roadmap.id}/progress`, {
        method: "PATCH",
        body: JSON.stringify({ completed_steps: next }),
      });
    } catch {
      // Ağ hatasında iyimser güncellemeyi geri al
      setCompleted(completed);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4">
      {/* Başlık + ilerleme */}
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Hedef Pozisyon
        </p>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {roadmap.target_role}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {roadmap.job_posting_id
            ? "Belirli bir ilana göre hazırlandı"
            : "Sektördeki genel beklentilere göre hazırlandı"}
        </p>

        <div className="mt-4">
          <div className="mb-1 flex items-baseline justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              {completed.length}/{total} adım tamamlandı
              {saving && <span className="ml-2 text-xs text-gray-400">kaydediliyor…</span>}
            </span>
            <span className="font-semibold tabular-nums text-blue-600 dark:text-blue-400">
              %{progress}
            </span>
          </div>
          <div
            className="h-2.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-blue-600 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </section>

      {/* Mevcut seviye + eksikler */}
      <div className="grid gap-4 sm:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
            Mevcut Seviye
          </h2>
          <ul className="space-y-2">
            {roadmap.current_strengths.map((s) => (
              <li key={s} className="flex gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span aria-hidden className="mt-0.5 shrink-0 text-green-600">✓</span>
                {s}
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">
            Eksik Yetkinlikler
          </h2>
          <ul className="space-y-2">
            {roadmap.gaps.map((g) => (
              <li key={g} className="flex gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span aria-hidden className="mt-0.5 shrink-0 text-amber-600">!</span>
                {g}
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* Gelişim planı — checklist */}
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
          Önerilen Adımlar
        </h2>
        <ol className="space-y-2">
          {roadmap.development_plan.map((step) => {
            const done = completed.includes(step.step);
            return (
              <li key={step.step}>
                <label
                  className={`flex cursor-pointer gap-3 rounded-xl border p-3 transition ${
                    done
                      ? "border-green-300 bg-green-50 dark:border-green-800 dark:bg-green-950/30"
                      : "border-gray-200 bg-white hover:border-blue-300 dark:border-gray-700 dark:bg-gray-900 dark:hover:border-blue-700"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={done}
                    onChange={() => toggle(step.step)}
                    className="mt-0.5 h-4 w-4 shrink-0 accent-green-600"
                  />
                  <div className="min-w-0">
                    <p
                      className={`text-sm ${
                        done
                          ? "text-gray-500 line-through dark:text-gray-500"
                          : "text-gray-900 dark:text-gray-100"
                      }`}
                    >
                      <span className="mr-1.5 font-semibold text-gray-400">
                        {step.step}.
                      </span>
                      {step.action}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      ⏱ Tahmini efor: {step.estimated_effort}
                    </p>
                  </div>
                </label>
              </li>
            );
          })}
        </ol>

        <p className="mt-5 rounded-lg bg-gray-50 p-3 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400">
          ⓘ Süre tahminleri düzenli çalışma varsayımına dayanan yaklaşık
          değerlerdir; kişiden kişiye değişir ve bir işe alım garantisi anlamına
          gelmez.
        </p>
      </section>
    </div>
  );
}
