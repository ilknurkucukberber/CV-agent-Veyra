"use client";

import Brand from "@/components/Brand";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import { register } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registered, setRegistered] = useState(false);

  const getStrength = (pass: string) => {
    let score = 0;
    if (pass.length >= 8) score++;
    if (/[A-Z]/.test(pass) && /[a-z]/.test(pass)) score++;
    if (/\d/.test(pass)) score++;
    if (/[!@#$%^&*(),.?":{}|<>\-_]/.test(pass)) score++;
    return score;
  };
  const strength = getStrength(password);
  
  const getStrengthColor = (s: number) => {
    if (s <= 1) return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]";
    if (s === 2) return "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.4)]";
    if (s === 3) return "bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.4)]";
    return "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]";
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!/[!@#$%^&*(),.?":{}|<>\-_]/.test(password)) {
      setError("Şifreniz en az bir noktalama işareti veya özel karakter içermelidir.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await register(email, password, fullName.trim());
      setRegistered(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kayıt oluşturulamadı");
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
        <div className="auth-kicker"><Sparkles size={13} /> YENİ KARİYER OTURUMU</div>
        <h1>Yeni seviyene<span>buradan başla<span className="auth-period">.</span></span></h1>
        <p>Tek bir hesapla CV analizi, iş eşleşmesi, mülakat provası ve kariyer rotana eriş.</p>
      </section>

      <section className="auth-panel-wrap">
        <div className="auth-panel-glow" aria-hidden="true" />
        <div className="auth-panel">
          <div className="auth-panel-head">
            <div>
              <span className="auth-index">BİR SONRAKİ ADIMIN</span>
              <h2>Hesabını oluştur.</h2>
              <p>Kariyer zekânı birkaç saniyede aktive et.</p>
            </div>
            <span className="auth-shield"><ShieldCheck size={21} /></span>
          </div>
          {registered ? (
            <div className="auth-form">
              <p className="auth-success-note">
                Hesabın oluşturuldu. {email} adresine doğrulama e-postan gönderime
                alındı. Gelen kutunu ve spam
                klasörünü kontrol edip bağlantıyı aç. E-posta ulaşmazsa giriş
                sayfasından yeniden doğrulama isteyebilirsin.
              </p>
              <Link href="/login" className="auth-submit">
                <span>Girişe dön</span>
                <span className="auth-submit-icon"><ArrowRight size={15} /></span>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="auth-form">
              <label>
                <span>Ad Soyad</span>
                <input required type="text" autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Adın ve soyadın" />
              </label>
              <label>
                <span>E-posta adresi</span>
                <input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="sen@ornek.com" />
              </label>
              <label>
                <span>Şifre</span>
                <input required minLength={8} type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="En az 8 karakter" />
                {password.length > 0 && (
                  <div className="mt-3">
                    <div className="flex gap-1.5">
                      {[1, 2, 3, 4].map((level) => (
                        <div 
                          key={level} 
                          className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                            strength >= level ? getStrengthColor(strength) : "bg-white/10"
                          }`} 
                        />
                      ))}
                    </div>
                    <p className="text-[11px] text-[#a0a6bc] mt-2 leading-relaxed">
                      Güçlü bir şifre için harf, rakam ve <span className={/[!@#$%^&*(),.?":{}|<>\-_]/.test(password) ? "text-emerald-400 font-medium transition-colors" : "text-white font-medium transition-colors"}>1 adet özel karakter</span> kullanın.
                    </p>
                  </div>
                )}
              </label>
              {error && <p className="auth-error">{error}</p>}
              <button type="submit" disabled={loading} className="auth-submit">
                <span>{loading ? "Hesap oluşturuluyor…" : "Ücretsiz hesabı oluştur"}</span>
                {!loading && <span className="auth-submit-icon"><ArrowRight size={15} /></span>}
              </button>
            </form>
          )}
          <div className="auth-panel-foot">
            <p>Zaten hesabın var mı? <Link href="/login">Giriş yap</Link></p>
          </div>
        </div>
      </section>
    </main>
  );
}
