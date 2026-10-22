"use client";

import { useState } from "react";
import ResumeGate from "@/components/ResumeGate";
import CareerRoadmapView from "@/components/CareerRoadmap";
import { CareerRoadmap } from "@/types/roadmap";
import { apiFetch, ApiError } from "@/lib/api";
import ToolPageShell from "@/components/ToolPageShell";

function CareerRoadmapRunner({ resumeId }: { resumeId: number }) {
  const [targetRole, setTargetRole] = useState("");
  const [roadmap, setRoadmap] = useState<CareerRoadmap | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        target_role: targetRole,
        resume_id: String(resumeId),
      });
      const data = await apiFetch<CareerRoadmap>(`/career-roadmap?${params.toString()}`);
      setRoadmap(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Yol haritası oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  if (roadmap) {
    return (
      <div className="space-y-4">
        <CareerRoadmapView roadmap={roadmap} />
        <div className="mx-auto max-w-3xl text-center">
          <button
            onClick={() => setRoadmap(null)}
            className="text-sm font-medium text-blue-600 hover:underline"
          >
            Farklı bir hedef pozisyon dene
          </button>
        </div>
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
          Hedef pozisyon
        </label>
        <input
          required
          minLength={2}
          type="text"
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          placeholder="Örn: Senior Backend Developer"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Yol haritası oluşturuluyor…" : "Kariyer Yol Haritamı Oluştur"}
      </button>
    </form>
  );
}

export default function CareerRoadmapDemoPage() {
  return (
    <ToolPageShell index="06" title="Kariyer Rotası" description="Hedef rolüne uzanan beceri, deneyim ve aksiyon adımlarını yapay zekâ ile haritala.">
      <ResumeGate>{(resumeId) => <CareerRoadmapRunner resumeId={resumeId} />}</ResumeGate>
    </ToolPageShell>
  );
}
