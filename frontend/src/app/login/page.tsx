"use client";

import CareerCanvas from "@/components/CareerCanvas";
import Brand from "@/components/Brand";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { login, resendVerificationEmail } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent">("idle");
  const [pointer, setPointer] = useState({ x: 0, y: 0 });

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setNeedsVerification(false);
    setResendState("idle");
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setNeedsVerification(true);
        setError(err.message);
      } else {
        setError(
          err instanceof ApiError
            ? err.message
            : "Giriş yapılamadı. Bilgilerini kontrol edip tekrar dene.",
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResendState("sending");
    setError(null);
    try {
      await resendVerificationEmail(email);
      setResendState("sent");
    } catch (err) {
      setResendState("idle");
      setError(err instanceof ApiError ? err.message : "Doğrulama isteği gönderilemedi. Lütfen tekrar dene.");
    }
  };

  return (
    <main
      className="auth-stage"
      onPointerMove={(event) => {
        const x = event.clientX / window.innerWidth - 0.5;
        const y = event.clientY / window.innerHeight - 0.5;
        setPointer({ x, y });
      }}
    >
      <div className="auth-aurora" aria-hidden="true" />
      <div className="auth-noise" aria-hidden="true" />
      <div
        className="auth-orbit-visual"
        aria-hidden="true"
        style={{
          transform: `translate3d(${pointer.x * 18}px, ${pointer.y * 12}px, 0) scale(1.03)`,
        }}
      />
      <div className="auth-vignette" aria-hidden="true" />

      <header className="auth-topbar">
        <Link href="/" className="auth-brand" aria-label="Veyra ana sayfa">
          <Brand />
        </Link>
      </header>

      <section className="auth-copy">
        <div className="auth-kicker">
          <Sparkles size={13} />
          KARİYERİN İÇİN YENİ BİR PERSPEKTİF
        </div>
        <h1>
          Hikâyen güçlü.
          <span>Sıradaki adım senin<span className="auth-period">.</span></span>
        </h1>
        <p>
          CV’ni analiz eden, doğru rolleri bulan ve seni her görüşmeye hazırlayan
          kişisel kariyer çalışma alanın.
        </p>
        <div className="auth-proof">
          <span><Check size={14} /> ATS analizi</span>
          <span><Check size={14} /> Akıllı eşleşme</span>
          <span><Check size={14} /> Mülakat simülasyonu</span>
        </div>
        <CareerCanvas />
      </section>

      <section className="auth-panel-wrap">
        <div className="auth-panel-glow" aria-hidden="true" />
        <div className="auth-panel">
          <div className="auth-panel-head">
            <div>
              <span className="auth-index">SENİN KARİYER ALANIN</span>
              <h2>Tekrar hoş geldin.</h2>
              <p>Kaldığın yerden, daha net bir hedefle devam et.</p>
            </div>
            <span className="auth-shield"><ShieldCheck size={21} /></span>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            <label>
              <span>E-posta adresi</span>
              <input
                required
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="sen@ornek.com"
              />
            </label>
            <label>
              <span className="auth-label-row">
                <span>Şifre</span>
                <Link href="/forgot-password" className="auth-forgot-link">Şifremi unuttum</Link>
              </span>
              <span className="auth-password">
                <input
                  required
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Şifreyi gizle" : "Şifreyi göster"}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </span>
            </label>

            {error && <p role="alert" className="auth-error">{error}</p>}
            {needsVerification && (
              resendState === "sent" ? (
                <p className="auth-success-note">
                  Doğrulama isteğin alındı. Gelen kutunu ve spam klasörünü kontrol et. E-posta ulaşmazsa daha sonra tekrar deneyebilirsin.
                </p>
              ) : (
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendState === "sending"}
                  className="auth-forgot-link"
                  style={{ textAlign: "left" }}
                >
                  {resendState === "sending" ? "Gönderiliyor…" : "Doğrulama linkini tekrar gönder"}
                </button>
              )
            )}

            <button type="submit" disabled={loading} className="auth-submit">
              <span>{loading ? "Sistem açılıyor…" : "Kariyer alanını aç"}</span>
              {!loading && <span className="auth-submit-icon"><ArrowRight size={15} /></span>}
            </button>
          </form>

          <div className="auth-panel-foot">
            <p>
              Hesabın yok mu?{" "}
              <Link href="/register">Ücretsiz başla</Link>
            </p>
          </div>
        </div>
      </section>

      <footer className="auth-footer">
        <span>VEYRA · 2026</span>
        <span>DAHA NET BİR CV. DAHA GÜÇLÜ BİR ADIM.</span>
      </footer>
    </main>
  );
}
