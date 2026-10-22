"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ResumeGate from "@/components/ResumeGate";
import InterviewPrep from "@/components/InterviewPrep";
import { InterviewSession } from "@/types/interview";
import { apiFetch, ApiError } from "@/lib/api";
import ToolPageShell from "@/components/ToolPageShell";

import LoadingPulse from "@/components/LoadingPulse";

const SESSION_TYPE_LABELS: Record<string, string> = {
  hr: "İK Görüşmesi",
  technical: "Teknik Görüşme",
  behavioral: "Davranışsal Görüşme",
};

function InterviewPrepRunner({ resumeId }: { resumeId: number }) {
  const router = useRouter();
  const [sessionType, setSessionType] = useState<"hr" | "technical" | "behavioral">("behavioral");
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<InterviewSession>("/interview/questions", {
        method: "POST",
        body: JSON.stringify({ resume_id: resumeId, session_type: sessionType }),
      });
      setSession(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sorular üretilemedi");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border border-white/10 bg-black/40 backdrop-blur shadow-xl">
        <LoadingPulse text="YAPAY ZEKA MÜLAKAT SENARYOSU VE SORULARI ÜRETİYOR..." />
      </div>
    );
  }

  if (session) {
    return (
      <div className="space-y-4">
        <InterviewPrep session={session} />
        <div className="mx-auto max-w-3xl text-center">
          <button
            onClick={() => router.push(`/interview-room-demo?session=${session.id}`)}
            className="tool-primary-action inline-flex items-center gap-2 transition"
          >
            Simülasyona başla
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6 rounded-2xl border border-white/10 bg-black/40 p-8 shadow-xl backdrop-blur">
      <div>
        <label className="mb-2 block text-xs font-semibold tracking-wide text-gray-400 uppercase">
          Görüşme Türü
        </label>
        <select
          value={sessionType}
          onChange={(e) => setSessionType(e.target.value as typeof sessionType)}
          className="w-full"
        >
          {Object.entries(SESSION_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <button
        onClick={generate}
        disabled={loading}
        className="tool-primary-action w-full transition"
      >
        Soruları Oluştur
      </button>
    </div>
  );
}

export default function InterviewPrepDemoPage() {
  return (
    <ToolPageShell index="05" title="Mülakat Stüdyosu" description="Pozisyona özel sorularla hazırlan, düşünce yapını güçlendir ve gerçek görüşmeden önce prova yap.">
      <ResumeGate>{(resumeId) => <InterviewPrepRunner resumeId={resumeId} />}</ResumeGate>
    </ToolPageShell>
  );
}
