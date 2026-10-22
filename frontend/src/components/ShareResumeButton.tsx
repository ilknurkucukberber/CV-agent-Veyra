"use client";

import { useEffect, useState } from "react";
import { Check, Copy, Link2, Trash2 } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

interface ShareInfo {
  token: string;
  revoked: boolean;
  created_at: string;
}

export default function ShareResumeButton({ resumeId }: { resumeId: number }) {
  const [share, setShare] = useState<ShareInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ShareInfo | null>(`/resumes/${resumeId}/share`)
      .then(setShare)
      .catch(() => setShare(null));
  }, [resumeId]);

  const shareUrl = share ? `${window.location.origin}/share/${share.token}` : "";

  const createShare = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ShareInfo>(`/resumes/${resumeId}/share`, { method: "POST" });
      setShare(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Paylaşım linki oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  const revokeShare = async () => {
    if (!confirm("Bu paylaşım linkini iptal etmek istediğine emin misin? Link artık çalışmaz.")) return;
    setLoading(true);
    try {
      await apiFetch(`/resumes/${resumeId}/share`, { method: "DELETE" });
      setShare(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Link iptal edilemedi");
    } finally {
      setLoading(false);
    }
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (share) {
    return (
      <div className="share-resume">
        <div className="share-resume-row">
          <Link2 size={13} />
          <input readOnly value={shareUrl} onFocus={(e) => e.target.select()} />
          <button onClick={copyLink} aria-label="Linki kopyala">
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
          <button onClick={revokeShare} disabled={loading} className="share-resume-revoke" aria-label="Paylaşımı iptal et">
            <Trash2 size={13} />
          </button>
        </div>
        <p className="share-resume-hint">
          Bu link, giriş yapmadan CV'ni ve en güncel ATS analizini salt-okunur gösterir. Bir mentor veya kariyer danışmanıyla paylaşabilirsin.
        </p>
      </div>
    );
  }

  return (
    <div className="share-resume">
      <button onClick={createShare} disabled={loading} className="share-resume-create">
        <Link2 size={14} />
        {loading ? "Oluşturuluyor…" : "Mentor ile paylaşım linki oluştur"}
      </button>
      {error && <p className="share-resume-error">{error}</p>}
    </div>
  );
}
