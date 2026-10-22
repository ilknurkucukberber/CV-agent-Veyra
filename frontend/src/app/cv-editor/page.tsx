"use client";

import { useEffect, useState } from "react";
import ResumeGate from "@/components/ResumeGate";
import CvEditor from "@/components/editor/CvEditor";
import { EditorVersion } from "@/types/resume";
import { JobPosting } from "@/types/job";
import { apiFetch, ApiError } from "@/lib/api";
import ToolPageShell from "@/components/ToolPageShell";
import Link from "next/link";

const EDIT_LEVEL_LABELS: Record<string, string> = {
  light: "Hafif düzenleme",
  targeted: "Hedefe göre düzenleme",
  from_scratch: "Baştan oluştur",
};

function CvEditorRunner({ resumeId }: { resumeId: number }) {
  const [versions, setVersions] = useState<EditorVersion[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [rewriting, setRewriting] = useState(false);
  const [editLevel, setEditLevel] = useState<"light" | "targeted" | "from_scratch">("light");
  const [jobPostings, setJobPostings] = useState<JobPosting[]>([]);
  const [targetJobPostingId, setTargetJobPostingId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadVersions = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<EditorVersion[]>(`/resumes/${resumeId}/versions`);
      setVersions(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Versiyonlar yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVersions();
    apiFetch<JobPosting[]>("/job-postings")
      .then(setJobPostings)
      .catch(() => setJobPostings([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeId]);

  const handleRewrite = async () => {
    setRewriting(true);
    setError(null);
    try {
      await apiFetch(`/resumes/${resumeId}/rewrite`, {
        method: "POST",
        body: JSON.stringify({
          edit_level: editLevel,
          target_job_posting_id:
            editLevel === "targeted" ? Number(targetJobPostingId) : null,
        }),
      });
      await loadVersions();
    } catch (e) {
      setError(
        e instanceof ApiError && e.status !== 400
          ? e.message
          : "Hedefe göre düzenleme için önce bir iş ilanı seçmelisin.",
      );
    } finally {
      setRewriting(false);
    }
  };

  if (loading) {
    return <p className="p-6 text-center text-sm text-gray-500">Yükleniyor…</p>;
  }

  return (
    <div className="space-y-4">
      <div className="cv-rewrite-console mx-auto max-w-4xl rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <div className="cv-rewrite-controls">
          <label>
            <span>Düzenleme seviyesi</span>
            <select
              value={editLevel}
              onChange={(e) => {
                setEditLevel(e.target.value as typeof editLevel);
                setError(null);
              }}
            >
              {Object.entries(EDIT_LEVEL_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          {editLevel === "targeted" && (
            <label className="cv-target-select">
              <span>Hedef iş ilanı</span>
              <select
                value={targetJobPostingId}
                onChange={(e) => setTargetJobPostingId(e.target.value)}
              >
                <option value="">Bir ilan seç</option>
                {jobPostings.map((posting) => (
                  <option key={posting.id} value={posting.id}>
                    {posting.title}{posting.company ? ` · ${posting.company}` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}

          <button
            onClick={handleRewrite}
            disabled={rewriting || (editLevel === "targeted" && !targetJobPostingId)}
            className="bg-blue-600"
          >
            {rewriting ? "Yeniden yazılıyor…" : "AI ile yeniden yaz"}
          </button>
        </div>

        {editLevel === "targeted" && jobPostings.length === 0 && (
          <p className="cv-target-empty">
            Henüz kayıtlı iş ilanı yok.{" "}
            <Link href="/job-match-demo">İş Eşleşmesi ekranından ilan ekle</Link>
          </p>
        )}
        {error && <p className="cv-editor-error">{error}</p>}
      </div>

      {versions && versions.length > 0 ? (
        <CvEditor initialVersions={versions} key={versions.map((v) => v.id).join(",")} />
      ) : (
        <p className="p-6 text-center text-sm text-gray-500">
          Henüz bir CV versiyonu yok. "AI ile yeniden yaz" ile ilk versiyonu oluşturun.
        </p>
      )}
    </div>
  );
}

export default function CvEditorPage() {
  return (
    <ToolPageShell index="04" title="CV Editör" description="Deneyimini hedef role göre yeniden kurgula; her versiyonu kontrollü biçimde karşılaştır." wide>
      <ResumeGate>{(resumeId) => <CvEditorRunner resumeId={resumeId} />}</ResumeGate>
    </ToolPageShell>
  );
}
