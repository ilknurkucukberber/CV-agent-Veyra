"use client";

import Brand from "@/components/Brand";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import { confirmEmailVerification } from "@/lib/auth";
import { ApiError } from "@/lib/api";

function VerifyEmailStatus() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("Doğrulama linki geçersiz. Lütfen e-postandaki linki tekrar aç.");
      return;
    }
    confirmEmailVerification(token)
      .then(() => setStatus("success"))
      .catch((e) => {
        setStatus("error");
        setError(e instanceof ApiError ? e.message : "Doğrulama başarısız oldu");
      });
  }, [token]);

  return (
    <section className="auth-panel-wrap">
      <div className="auth-panel-glow" aria-hidden="true" />
      <div className="auth-panel">
        <div className="auth-panel-head">
          <div>
            <span className="auth-index">00 / VERIFY</span>
            <h2>E-posta doğrulama.</h2>
            <p>Hesabını aktive ediyoruz.</p>
          </div>
          <span className="auth-shield"><ShieldCheck size={21} /></span>
        </div>

        {status === "loading" && (
          <p className="auth-form" style={{ color: "rgba(255,255,255,.6)", fontSize: 13 }}>
            Doğrulanıyor…
          </p>
        )}

        {status === "success" && (
          <div className="auth-form">
            <p className="auth-success-note">
              E-posta adresin doğrulandı. Artık giriş yapabilirsin.
            </p>
            <Link href="/login" className="auth-submit">
              <span>Giriş yap</span>
              <span className="auth-submit-icon"><ArrowRight size={15} /></span>
            </Link>
          </div>
        )}

        {status === "error" && (
          <div className="auth-form">
            <p className="auth-error" role="alert">{error}</p>
            <Link href="/login" className="auth-submit">
              <span>Girişe dön</span>
              <span className="auth-submit-icon"><ArrowRight size={15} /></span>
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}

export default function VerifyEmailPage() {
  return (
    <main className="auth-stage">
      <div className="auth-aurora" aria-hidden="true" />
      <div className="auth-noise" aria-hidden="true" />
      <div className="auth-orbit-visual" aria-hidden="true" />
      <div className="auth-vignette" aria-hidden="true" />

      <header className="auth-topbar">
        <Link href="/" className="auth-brand">
          <Brand />
        </Link>
      </header>

      <section className="auth-copy">
        <div className="auth-kicker"><Sparkles size={13} /> HESAP AKTİVASYONU</div>
        <h1>Son bir<span>adım kaldı<span className="auth-period">.</span></span></h1>
        <p>E-posta adresini doğrulayıp kariyer alanına giriş yap.</p>
      </section>

      <Suspense fallback={null}>
        <VerifyEmailStatus />
      </Suspense>
    </main>
  );
}
