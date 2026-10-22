"use client";

import { useMemo, useState } from "react";
import {
  AnswerEvaluation,
  FEEDBACK_LABELS,
  InterviewSession,
  SESSION_TYPE_LABELS,
  SOURCE_LABELS,
} from "@/types/interview";
import { apiFetch, ApiError } from "@/lib/api";

type Phase = "answering" | "reviewing" | "finished";

/** Sunucu erişilemediğinde demo amaçlı yerel değerlendirme üretir. */
function localFallbackEvaluation(
  questionId: number,
  question: string,
  userAnswer: string,
  remaining: number,
  nextId: number | null,
): AnswerEvaluation {
  const words = userAnswer.trim().split(/\s+/).filter(Boolean).length;
  const thin = words < 40;
  return {
    question_id: questionId,
    question,
    user_answer: userAnswer,
    feedback: {
      too_general: thin,
      missing_technical_detail: thin,
      missing_position_connection: thin,
      structure_notes: thin
        ? "Cevap kısa kaldı: Durum, Görev, Eylem ve Sonuç bileşenlerinden hangilerinin eksik olduğunu gözden geçirin. Attığınız somut adımları ve sonucun gözlemlenebilir etkisini ekleyebilirsiniz."
        : "Cevap yapısal olarak yeterli görünüyor. Sonuç bölümünü gözlemlenebilir bir etkiyle kapatmak anlatımı güçlendirir.",
    },
    suggested_improved_answer:
      "Durum: [bağlamı yazın]\nGörev: [sorumluluğunuzu yazın]\nEylem: [attığınız adımları yazın]\nSonuç: [sonucun etkisini yazın]",
    follow_up_question: thin ? "Bu süreçte en zorlandığınız kısım neydi?" : null,
    next_question_id: nextId,
    remaining_questions: remaining,
  };
}

export default function InterviewRoom({
  session,
  // false verilirse sunucuya gidilmez, yerel değerlendirme kullanılır (demo/çevrimdışı).
  useServer = true,
}: {
  session: InterviewSession;
  useServer?: boolean;
}) {
  const questions = useMemo(
    () => [...session.questions].sort((a, b) => a.order_index - b.order_index),
    [session.questions],
  );

  const [index, setIndex] = useState(0);
  const [draft, setDraft] = useState("");
  const [phase, setPhase] = useState<Phase>("answering");
  const [evaluation, setEvaluation] = useState<AnswerEvaluation | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const current = questions[index];
  const isLast = index === questions.length - 1;

  const submit = async () => {
    if (!draft.trim()) return;
    setSubmitting(true);
    setError(null);

    const nextId = isLast ? null : questions[index + 1].id;
    const remaining = questions.length - index - 1;

    try {
      if (useServer) {
        const result = await apiFetch<AnswerEvaluation>(
          `/interview/sessions/${session.id}/answer`,
          {
            method: "POST",
            body: JSON.stringify({ question_id: current.id, user_answer: draft }),
          },
        );
        setEvaluation(result);
      } else {
        setEvaluation(
          localFallbackEvaluation(current.id, current.question, draft, remaining, nextId),
        );
      }
      setPhase("reviewing");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cevap gönderilemedi");
    } finally {
      setSubmitting(false);
    }
  };

  const goNext = () => {
    if (isLast) {
      setPhase("finished");
      return;
    }
    setIndex((i) => i + 1);
    setDraft("");
    setEvaluation(null);
    setPhase("answering");
  };

  if (phase === "finished") {
    return (
      <div className="mx-auto w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <p className="text-4xl" aria-hidden>
          ✅
        </p>
        <h1 className="mt-2 text-xl font-bold text-gray-900 dark:text-gray-100">
          Simülasyon tamamlandı
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {questions.length} sorunun tamamını yanıtladınız. Cevaplarınız ve geri
          bildirimler oturumda kayıtlı.
        </p>
        <button
          onClick={() => {
            setIndex(0);
            setDraft("");
            setEvaluation(null);
            setPhase("answering");
          }}
          className="mt-5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
        >
          Baştan başla
        </button>
      </div>
    );
  }

  const activeFlags = evaluation
    ? (Object.keys(FEEDBACK_LABELS) as (keyof typeof FEEDBACK_LABELS)[]).filter(
        (key) => evaluation.feedback[key],
      )
    : [];

  return (
    <div className="mx-auto w-full max-w-2xl space-y-4">
      {/* Başlık + ilerleme */}
      <header className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-baseline justify-between">
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {SESSION_TYPE_LABELS[session.session_type] ?? session.session_type}
          </h1>
          <span className="text-sm tabular-nums text-gray-500">
            Soru {index + 1}/{questions.length}
          </span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <div
            className="h-full rounded-full bg-blue-600 transition-all"
            style={{ width: `${((index + (phase === "reviewing" ? 1 : 0)) / questions.length) * 100}%` }}
          />
        </div>
      </header>

      {/* Soru */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-gray-300 bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300">
            {SOURCE_LABELS[current.source ?? "general"]}
          </span>
          {current.category && (
            <span className="text-xs text-gray-500">{current.category}</span>
          )}
          {current.star_applicable && (
            <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
              ★ STAR
            </span>
          )}
        </div>
        <p className="text-base text-gray-900 dark:text-gray-100">{current.question}</p>
      </section>

      {/* Cevap alanı */}
      {phase === "answering" ? (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
          <label
            htmlFor="answer"
            className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300"
          >
            Cevabınız
          </label>
          <textarea
            id="answer"
            rows={7}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              current.star_applicable
                ? "Durum, göreviniz, attığınız adımlar ve sonuç…"
                : "Cevabınızı yazın…"
            }
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
          <div className="mt-2 flex items-center gap-3">
            <button
              onClick={submit}
              disabled={!draft.trim() || submitting}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition enabled:hover:bg-blue-700 disabled:opacity-40"
            >
              {submitting ? "Değerlendiriliyor…" : "Cevabı gönder"}
            </button>
            <span className="text-xs text-gray-400">
              {draft.trim().split(/\s+/).filter(Boolean).length} kelime
            </span>
            {error && <span className="text-xs text-red-600">{error}</span>}
          </div>
        </section>
      ) : (
        evaluation && (
          <>
            {/* Kullanıcının cevabı */}
            <section className="rounded-2xl border border-gray-200 bg-gray-50 p-5 dark:border-gray-700 dark:bg-gray-800/50">
              <h2 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Cevabınız
              </h2>
              <p className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                {evaluation.user_answer}
              </p>
            </section>

            {/* Geri bildirim */}
            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
                Geri Bildirim
              </h2>
              {activeFlags.length > 0 ? (
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {activeFlags.map((key) => (
                    <span
                      key={key}
                      className="rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                    >
                      {FEEDBACK_LABELS[key]}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mb-3 text-xs font-medium text-green-700 dark:text-green-400">
                  ✓ Yapısal bir eksik işaretlenmedi
                </p>
              )}
              <p className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                {evaluation.feedback.structure_notes}
              </p>
            </section>

            {/* Geliştirilmiş cevap */}
            <section className="rounded-2xl border border-green-200 bg-green-50 p-5 dark:border-green-900 dark:bg-green-950/30">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-green-800 dark:text-green-400">
                Geliştirilmiş Cevap Önerisi
              </h2>
              <p className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200">
                {evaluation.suggested_improved_answer}
              </p>
              <p className="mt-3 text-xs text-gray-600 dark:text-gray-400">
                ⓘ Bu öneri yalnızca sizin cevabınızdaki bilgilerle sınırlıdır; köşeli
                parantezli yerleri kendi somut bilgilerinizle doldurun.
              </p>
            </section>

            {evaluation.follow_up_question && (
              <section className="rounded-2xl border border-teal-200 bg-teal-50 p-5 dark:border-teal-900 dark:bg-teal-950/30">
                <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-teal-800 dark:text-teal-400">
                  Olası Takip Sorusu
                </h2>
                <p className="text-sm text-gray-800 dark:text-gray-200">
                  {evaluation.follow_up_question}
                </p>
              </section>
            )}

            <button
              onClick={goNext}
              className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700"
            >
              {isLast
                ? "Simülasyonu bitir"
                : `Sonraki soru (${evaluation.remaining_questions} kaldı)`}
            </button>
          </>
        )
      )}
    </div>
  );
}
