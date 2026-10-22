"use client";

import Brand from "@/components/Brand";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import { requestPasswordReset } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "İstek gönderilemedi, lütfen tekrar dene");
    } finally {
      setLoading(false);
    }
  };

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
        <div className="auth-kicker"><Sparkles size={13} /> HESAP KURTARMA</div>
        <h1>Şifreni<span>sıfırlayalım<span className="auth-period">.</span></span></h1>
        <p>E-posta adresini gir, sana bir sıfırlama linki gönderelim.</p>
      </section>

      <section className="auth-panel-wrap">
        <div className="auth-panel-glow" aria-hidden="true" />
        <div className="auth-panel">
          <div className="auth-panel-head">
            <div>
              <span className="auth-index">00 / RECOVER</span>
              <h2>Şifremi unuttum.</h2>
              <p>Kayıtlı e-posta adresini gir, sıfırlama linkini gönderelim.</p>
            </div>
            <span className="auth-shield"><ShieldCheck size={21} /></span>
          </div>

          {sent ? (
            <div className="auth-form">
              <p className="auth-success-note">
                Şifre sıfırlama isteğin alındı. Bu adresle aktif bir hesap varsa
                e-posta gönderimi denenir. Gelen kutunu ve spam klasörünü kontrol et.
              </p>
              <Link href="/login" className="auth-submit">
                <span>Girişe dön</span>
                <span className="auth-submit-icon"><ArrowRight size={15} /></span>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="auth-form">
              <label>
                <span>E-posta adresi</span>
                <input
                  required
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="sen@ornek.com"
                />
              </label>
              {error && <p className="auth-error">{error}</p>}
              <button type="submit" disabled={loading} className="auth-submit">
                <span>{loading ? "Gönderiliyor…" : "Sıfırlama linki gönder"}</span>
                {!loading && <span className="auth-submit-icon"><ArrowRight size={15} /></span>}
              </button>
            </form>
          )}

          <div className="auth-panel-foot">
            <p>Şifreni hatırladın mı? <Link href="/login">Giriş yap</Link></p>
          </div>
        </div>
      </section>
    </main>
  );
}
