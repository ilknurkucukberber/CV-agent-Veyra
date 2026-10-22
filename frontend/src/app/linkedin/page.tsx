"use client";

import { useState } from "react";
import ResumeGate from "@/components/ResumeGate";
import LinkedInResultCard from "@/components/LinkedInResultCard";
import { LinkedInOptimizeResult } from "@/types/linkedin";
import { apiFetch, ApiError } from "@/lib/api";
import ToolPageShell from "@/components/ToolPageShell";

function LinkedInOptimizer({ resumeId }: { resumeId: number }) {
  const [targetRole, setTargetRole] = useState("");
  const [result, setResult] = useState<LinkedInOptimizeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const optimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ resume_id: String(resumeId) });
      if (targetRole.trim()) params.set("target_role", targetRole.trim());
      const data = await apiFetch<LinkedInOptimizeResult>(
        `/linkedin/optimize?${params.toString()}`,
        { method: "POST" },
      );
      setResult(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Öneriler oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="flex flex-col items-center gap-4">
        <LinkedInResultCard result={result} />
        <button
          onClick={() => setResult(null)}
          className="text-sm font-medium text-blue-600 hover:underline"
        >
          Yeniden oluştur
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
          Hedef pozisyon <span className="text-gray-400">(opsiyonel)</span>
        </label>
        <input
          type="text"
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          placeholder="Örn: Backend Developer"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        onClick={optimize}
        disabled={loading}
        className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Öneriler oluşturuluyor…" : "LinkedIn Profilimi Optimize Et"}
      </button>
    </div>
  );
}

export default function LinkedInPage() {
  return (
    <ToolPageShell index="07" title="LinkedIn Zekâsı" description="Profil başlığını, özetini ve görünürlük sinyallerini hedeflediğin role göre optimize et.">
      <div className="mx-auto w-full max-w-2xl">
        <ResumeGate>{(resumeId) => <LinkedInOptimizer resumeId={resumeId} />}</ResumeGate>
      </div>
    </ToolPageShell>
  );
}
