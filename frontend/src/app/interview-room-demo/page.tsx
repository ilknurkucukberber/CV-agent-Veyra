"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import InterviewRoom from "@/components/InterviewRoom";
import { InterviewSession } from "@/types/interview";
import { apiFetch, ApiError } from "@/lib/api";
import ToolPageShell from "@/components/ToolPageShell";

export default function InterviewRoomDemoPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");

  const [session, setSession] = useState<InterviewSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    apiFetch<InterviewSession>(`/interview/sessions/${sessionId}`)
      .then(setSession)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Oturum yüklenemedi"));
  }, [sessionId]);

  if (!sessionId) {
    return (
      <main className="tool-page flex items-center justify-center">
        <div className="max-w-md rounded-2xl border border-gray-200 bg-white p-6 text-center shadow-sm dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Bir mülakat simülasyonu başlatmak için önce hazırlık ekranından soru üretmelisiniz.
          </p>
          <Link
            href="/interview-prep-demo"
            className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
          >
            Mülakat Hazırlığına Git
          </Link>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="tool-page flex items-center justify-center">
        <p className="text-sm text-red-600">{error}</p>
      </main>
    );
  }

  if (!session) {
    return (
      <main className="tool-page flex items-center justify-center">
        <p className="text-sm text-gray-500">Yükleniyor…</p>
      </main>
    );
  }

  return (
    <ToolPageShell index="05.1" title="Canlı Mülakat" description="Yanıtlarını gerçek zamanlı yapılandır, iletişim gücünü ve örneklerini kontrollü biçimde geliştir." wide>
      <InterviewRoom session={session} />
    </ToolPageShell>
  );
}
