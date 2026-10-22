"use client";

import Brand from "@/components/Brand";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import { confirmPasswordReset } from "@/lib/auth";
import { ApiError } from "@/lib/api";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!token) {
      setError("Sıfırlama linki geçersiz. Lütfen linki e-postandan tekrar aç.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Şifreler eşleşmiyor.");
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(token, password);
      setDone(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Şifre güncellenemedi");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="auth-panel-wrap">
      <div className="auth-panel-glow" aria-hidden="true" />
      <div className="auth-panel">
        <div className="auth-panel-head">
          <div>
            <span className="auth-index">00 / RESET</span>
            <h2>Yeni şifre belirle.</h2>
            <p>Hesabına erişimini yeniden kazan.</p>
          </div>
          <span className="auth-shield"><ShieldCheck size={21} /></span>
        </div>

        {!token && (
          <p className="auth-error" role="alert">
            Bu sayfaya doğrudan erişemezsin; e-postana gönderilen sıfırlama
            linkini kullanman gerekiyor.
          </p>
        )}

        {done ? (
          <p className="auth-success-note">
            Şifren güncellendi. Giriş sayfasına yönlendiriliyorsun…
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            <label>
              <span>Yeni şifre</span>
              <input
                required
                minLength={8}
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="En az 8 karakter"
                disabled={!token}
              />
            </label>
            <label>
              <span>Yeni şifre (tekrar)</span>
              <input
                required
                minLength={8}
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Şifreni tekrar gir"
                disabled={!token}
              />
            </label>
            {error && <p className="auth-error">{error}</p>}
            <button type="submit" disabled={loading || !token} className="auth-submit">
              <span>{loading ? "Güncelleniyor…" : "Şifreyi güncelle"}</span>
              {!loading && <span className="auth-submit-icon"><ArrowRight size={15} /></span>}
            </button>
          </form>
        )}

        <div className="auth-panel-foot">
          <p>Şifreni hatırladın mı? <Link href="/login">Giriş yap</Link></p>
        </div>
      </div>
    </section>
  );
}

export default function ResetPasswordPage() {
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
        <h1>Yeniden<span>erişim kazan<span className="auth-period">.</span></span></h1>
        <p>Yeni şifreni belirle ve kaldığın yerden devam et.</p>
      </section>

      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
