"use client";

import { useEffect, useRef, useState } from "react";
import { Check, FileText, LoaderCircle, Trash2, UploadCloud } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";

const STORAGE_KEY = "active_resume_id";

interface ResumeStatus {
  id: number;
  parse_status: "pending" | "processing" | "completed" | "failed";
  parse_error: string | null;
  updated_at: string;
}

interface ResumeSummary {
  id: number;
  title: string;
  original_filename: string | null;
  parse_status: "pending" | "processing" | "completed" | "failed";
  is_primary: boolean;
  created_at: string;
}

/**
 * localStorage'daki aktif CV kaybolduğunda (farklı cihaz/tarayıcı, temizlenen
 * veri) kullanıcının önceden yüklediği CV'lere erişebilmesi için sunucudan
 * geçmiş CV listesini gösterir; yeniden yüklemeye zorlamaz.
 */
function ResumeHistoryPicker({
  onSelect,
}: {
  onSelect: (id: number) => void;
}) {
  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);

  useEffect(() => {
    apiFetch<ResumeSummary[]>("/resumes")
      .then(setResumes)
      .catch(() => setResumes([]));
  }, []);

  if (!resumes || resumes.length === 0) return null;

  return (
    <div className="resume-history-picker">
      <p className="resume-history-title">Daha önce yüklediğin CV'ler</p>
      <ul>
        {resumes.map((r) => (
          <li key={r.id}>
            <button type="button" onClick={() => onSelect(r.id)} disabled={r.parse_status !== "completed"}>
              <FileText size={14} />
              <span>{r.title}</span>
              {r.is_primary && <span className="resume-primary-badge">Birincil</span>}
              {r.parse_status !== "completed" && <span className="resume-history-status">{r.parse_status}</span>}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Sayfanın çalışabilmesi için ayrıştırılmış bir CV gerektiğinde kullanılır.
 * localStorage'daki aktif CV'yi kontrol eder; yoksa yükleme formu gösterir,
 * parse tamamlanana kadar durumu poll eder, sonra children'ı resumeId ile render eder.
 */
export default function ResumeGate({
  children,
}: {
  children: (resumeId: number) => React.ReactNode;
}) {
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [status, setStatus] = useState<ResumeStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollStatus = (id: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const check = async () => {
      try {
        const data = await apiFetch<ResumeStatus>(`/resumes/${id}/status`);
        setStatus(data);
        setError(null);
        if (data.parse_status === "completed" || data.parse_status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (e) {
        if (e instanceof ApiError && (e.status === 401 || e.status === 404)) {
          localStorage.removeItem(STORAGE_KEY);
          setResumeId(null);
          if (pollRef.current) clearInterval(pollRef.current);
        } else {
          setError(e instanceof Error ? e.message : "CV durumu kontrol edilemedi. Bağlantı yeniden deneniyor.");
        }
      }
    };
    check();
    pollRef.current = setInterval(check, 2000);
  };

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const id = Number(stored);
      setResumeId(id);
      pollStatus(id);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await apiFetch<{ id: number }>("/resumes/upload", {
        method: "POST",
        body: formData,
      });
      localStorage.setItem(STORAGE_KEY, String(data.id));
      setResumeId(data.id);
      setStatus(null);
      pollStatus(data.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "CV yüklenemedi");
    } finally {
      setUploading(false);
    }
  };

  const retryParse = async () => {
    if (!resumeId || retrying) return;
    setRetrying(true);
    setError(null);
    try {
      await apiFetch(`/resumes/${resumeId}/retry-parse`, { method: "POST" });
      setStatus(null);
      pollStatus(resumeId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "CV yeniden işlenemedi.");
    } finally {
      setRetrying(false);
    }
  };

  const reset = () => {
    localStorage.removeItem(STORAGE_KEY);
    setResumeId(null);
    setStatus(null);
    setError(null);
    if (pollRef.current) clearInterval(pollRef.current);
  };

  const selectExisting = (id: number) => {
    localStorage.setItem(STORAGE_KEY, String(id));
    setResumeId(id);
    setStatus(null);
    setError(null);
    pollStatus(id);
  };

  const deleteActive = async () => {
    if (!resumeId) return;
    if (!confirm("Bu CV'yi silmek istediğine emin misin? Bu işlem geri alınamaz.")) return;
    try {
      await apiFetch(`/resumes/${resumeId}`, { method: "DELETE" });
    } catch {
      // Sunucuda zaten silinmişse de aktif CV referansını temizlemeye devam et.
    }
    reset();
  };

  if (resumeId && status?.parse_status === "completed") {
    return (
      <div>
        <div className="resume-active-bar">
          <span><i><Check size={13} /></i> CV #{resumeId} aktif ve analize hazır</span>
          <span className="resume-active-actions">
            <button onClick={reset}>Farklı CV yükle</button>
            <button onClick={deleteActive} className="resume-delete-btn" aria-label="Bu CV'yi sil">
              <Trash2 size={13} />
            </button>
          </span>
        </div>
        {children(resumeId)}
      </div>
    );
  }

  return (
    <div className="resume-gate mx-auto max-w-2xl">
      <div className="resume-gate-head">
        <span className="resume-gate-icon"><FileText size={21} /></span>
        <div>
          <span className="resume-gate-index">DOCUMENT INPUT / 01</span>
          <h2>CV’ni sisteme tanıt.</h2>
          <p>Analiz motorunu başlatmak için güncel CV dosyanı yükle.</p>
        </div>
      </div>

      {resumeId && status && status.parse_status !== "failed" && (
        <div className="resume-processing">
          <LoaderCircle size={16} />
          <span>{status.parse_status === "pending" ? "CV işleme sırası bekleniyor…" : "CV metni okunuyor ve ayrıştırılıyor…"}</span>
        </div>
      )}
      {resumeId && status?.parse_status === "failed" && (
        <div className="resume-failed">
          <p>
            CV ayrıştırılamadı: {status.parse_error?.includes("RetryError")
              ? "Yapay zekâ servisi isteği tamamlayamadı. Sağlayıcı bağlantısı ve API anahtarı kontrol edilmeli."
              : status.parse_error}
          </p>
          <button
            onClick={retryParse}
            disabled={retrying}
          >
            {retrying ? "Başlatılıyor…" : "Yeniden işle"}
          </button>
          <button onClick={reset} disabled={retrying}>Farklı dosya yükle</button>
        </div>
      )}

      {!resumeId && (
        <label className={`resume-dropzone ${uploading ? "is-uploading" : ""}`}>
          <input
            type="file"
            accept=".pdf,.docx,.jpg,.jpeg,.png"
            disabled={uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload(file);
            }}
          />
          <span className="resume-upload-icon">
            {uploading ? <LoaderCircle size={22} /> : <UploadCloud size={22} />}
          </span>
          <span className="resume-upload-copy">
            <strong>{uploading ? "CV sisteme aktarılıyor…" : "Dosyanı seç ve analizi başlat"}</strong>
            <small>PDF, DOCX, JPG veya PNG · Maksimum 10 MB</small>
          </span>
          <span className="resume-upload-action">Dosya seç</span>
        </label>
      )}
      {error && <p className="resume-upload-error">{error}</p>}
      {!resumeId && <ResumeHistoryPicker onSelect={selectExisting} />}
    </div>
  );
}
