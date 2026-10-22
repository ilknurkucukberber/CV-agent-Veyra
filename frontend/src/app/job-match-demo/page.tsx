"use client";

import { useState } from "react";
import ResumeGate from "@/components/ResumeGate";
import JobMatchCard from "@/components/JobMatchCard";
import { JobMatch, JobPosting } from "@/types/job";
import { apiFetch, ApiError } from "@/lib/api";
import ToolPageShell from "@/components/ToolPageShell";

function JobMatchRunner({ resumeId }: { resumeId: number }) {
  const [rawText, setRawText] = useState("");
  const [posting, setPosting] = useState<JobPosting | null>(null);
  const [match, setMatch] = useState<JobMatch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMatch(null);
    try {
      const createdPosting = await apiFetch<JobPosting>("/job-postings", {
        method: "POST",
        body: JSON.stringify({ raw_text: rawText }),
      });
      setPosting(createdPosting);

      const matchResult = await apiFetch<JobMatch>(
        `/job-postings/${createdPosting.id}/match?resume_id=${resumeId}`,
        { method: "POST" },
      );
      setMatch(matchResult);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status !== 503
          ? err.message
          : "İlan metni şu anda ayrıştırılamadı. Metni sadeleştirip yeniden deneyin.",
      );
    } finally {
      setLoading(false);
    }
  };

  if (match) {
    return (
      <div className="flex flex-col items-center gap-4">
        <JobMatchCard match={match} posting={posting ?? undefined} />
        <button
          onClick={() => {
            setMatch(null);
            setPosting(null);
            setRawText("");
          }}
          className="text-sm font-medium text-blue-600 hover:underline"
        >
          Başka bir ilan dene
        </button>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto max-w-xl space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900"
    >
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
          İş ilanı metni
        </label>
        <textarea
          required
          minLength={50}
          rows={10}
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="İlan metnini buraya yapıştırın (en az 50 karakter)…"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Eşleştiriliyor…" : "CV'nizle Eşleştirin"}
      </button>
    </form>
  );
}

export default function JobMatchDemoPage() {
  return (
    <ToolPageShell index="03" title="İş Eşleşmesi" description="İlanın gerçek beklentilerini CV sinyallerinle karşılaştır ve başvuru stratejini güçlendir.">
      <div className="mx-auto w-full max-w-2xl">
        <ResumeGate>{(resumeId) => <JobMatchRunner resumeId={resumeId} />}</ResumeGate>
      </div>
    </ToolPageShell>
  );
}
