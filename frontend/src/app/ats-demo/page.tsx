"use client";

import { useState } from "react";
import ResumeGate from "@/components/ResumeGate";
import AtsResultCard from "@/components/AtsResultCard";
import ShareResumeButton from "@/components/ShareResumeButton";
import { AtsAnalysis } from "@/types/ats";
import { apiFetch, ApiError } from "@/lib/api";
import ToolPageShell from "@/components/ToolPageShell";

import LoadingPulse from "@/components/LoadingPulse";

function AtsAnalysisRunner({ resumeId }: { resumeId: number }) {
  const [analysis, setAnalysis] = useState<AtsAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<AtsAnalysis>(`/resumes/${resumeId}/ats-analysis`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setAnalysis(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Analiz oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border border-white/10 bg-black/40 backdrop-blur shadow-xl">
        <LoadingPulse text="YAPAY ZEKA CV'NİZİ ATS GÖZÜYLE ANALİZ EDİYOR..." />
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border border-white/10 bg-black/40 p-8 text-center shadow-xl backdrop-blur">
        <p className="text-sm text-gray-400">
          CV'niz hazır. ATS uyumluluk analizini başlatabilirsiniz.
        </p>
        <button
          onClick={runAnalysis}
          disabled={loading}
          className="tool-primary-action mt-6 inline-flex items-center gap-2 transition"
        >
          ATS Analizini Başlat
        </button>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-6">
      <AtsResultCard analysis={analysis} />
      <ShareResumeButton resumeId={resumeId} />
      <button
        onClick={runAnalysis}
        disabled={loading}
        className="text-xs font-semibold tracking-wider text-cobalt hover:text-aqua transition disabled:opacity-50 uppercase"
      >
        YENİDEN ANALİZ ET
      </button>
    </div>
  );
}

export default function AtsDemoPage() {
  return (
    <ToolPageShell index="02" title="CV Analizi" description="CV’ni işe alım sistemlerinin gözünden incele; güçlü ve geliştirilmesi gereken sinyalleri netleştir.">
      <div className="mx-auto w-full max-w-2xl">
        <ResumeGate>{(resumeId) => <AtsAnalysisRunner resumeId={resumeId} />}</ResumeGate>
      </div>
    </ToolPageShell>
  );
}
