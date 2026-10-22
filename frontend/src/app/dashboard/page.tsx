'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ArrowUpRight, Briefcase, Check, FileText, ScanSearch, Video } from 'lucide-react';
import { API_BASE, getToken } from '@/lib/api';

interface DashboardSummary {
  ats_score: number | null;
  active_applications_count: number;
  status_distribution: Record<string, number>;
  cv_version_count: number;
  upcoming_interviews: Array<{ company: string; position: string; status: string }>;
  profile_completion_percentage: number;
}
const LABELS: Record<string,string> = { saved:'Kaydedilen', applied:'Başvurulan', hr_interview:'İK görüşmesi', technical_interview:'Teknik görüşme', offer:'Teklif', rejected:'Olumsuz' };

export default function DashboardPage() {
  const [data,setData] = useState<DashboardSummary|null>(null);
  const [loading,setLoading] = useState(true);
  useEffect(()=>{(async()=>{try{const r=await fetch(`${API_BASE}/dashboard/summary`,{headers:{Authorization:`Bearer ${getToken()}`}});if(r.ok)setData(await r.json());}catch(e){console.error(e);}finally{setLoading(false);}})();},[]);
  if(loading||!data) return <Skeleton />;
  const next = data.profile_completion_percentage < 80
    ? {title:'Profilini tamamla',copy:'Eşleşme kalitesini artırmak için eksik kariyer verilerini tamamla.',href:'/profile'}
    : {title:'CV stratejini güçlendir',copy:'Bir ilan seç, analizi çalıştır ve başvurunu pozisyona göre hassaslaştır.',href:'/ats-demo'};

  return <div className="mx-auto max-w-[1520px] px-5 pb-20 pt-7 sm:px-8 lg:px-10 lg:pt-10">
    <header className="flex flex-col gap-6 border-b border-white/[.08] pb-8 xl:flex-row xl:items-end xl:justify-between">
      <div className="mask-reveal"><p className="dashboard-eyebrow">VEYRA / GENEL BAKIŞ</p>
        <h1 className="editorial-title max-w-5xl text-[clamp(2.8rem,4.5vw,4.4rem)] font-black text-[#f4f1eb]">Bir sonraki adımın.</h1>
        <p className="mt-5 max-w-xl text-base leading-relaxed text-[#a0a6bc]">Deneyimini fırsata dönüştür. CV’n, başvuruların ve kariyer hedeflerin bir arada.</p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link href="/cv-editor" className="flex min-h-11 items-center gap-2 rounded-[10px] border border-white/[.1] px-4 text-xs font-semibold text-[#c5c7cd] hover:border-white/20 hover:bg-white/[.04] hover:text-white"><FileText size={16}/>CV’yi aç</Link>
        <Link href="/applications" className="scanline flex min-h-11 items-center gap-2 rounded-[10px] bg-[#9b8afb] px-4 text-xs font-semibold text-[#211a33] hover:-translate-y-0.5 hover:bg-[#ae9eff]">Başvuru ekle<ArrowUpRight size={16}/></Link>
      </div>
    </header>

    <section className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
      <article className="executive-card intelligence-hero executive-grid scanline flex min-h-[430px] flex-col justify-between overflow-hidden p-6 sm:p-8">
        <div className="flex items-start justify-between gap-6">
          <div className="relative z-10"><p className="micro-label text-[#d0c6ff]">SANA ÖZEL · SIRADAKİ ADIM</p><h2 className="mt-7 max-w-3xl text-[clamp(2.2rem,3.6vw,3.8rem)] font-black leading-[1.02] tracking-[-.035em] text-white">{next.title}</h2></div>
          <span className="font-mono text-xs text-[#555a64]">01</span>
        </div>
        <div className="relative z-10 flex flex-col gap-6 border-t border-white/[.08] pt-6 sm:flex-row sm:items-end sm:justify-between">
          <p className="max-w-lg text-sm leading-relaxed text-[#b0b7cc]">{next.copy}</p>
          <Link href={next.href} className="group flex min-h-12 items-center justify-center gap-3 rounded-[10px] bg-white px-5 text-xs font-semibold text-[#10121c] hover:-translate-y-0.5 hover:bg-[#dfe4ff]">Devam et<ArrowRight size={16} className="transition-transform group-hover:translate-x-1"/></Link>
        </div>
      </article>
      <article className="executive-card flex min-h-[390px] flex-col justify-between p-6 sm:p-8">
        <div className="flex items-center justify-between"><p className="micro-label text-[#9ba2b7]">ATS hazırlık skoru</p><i className="status-pulse size-2 rounded-full bg-[#9b8afb]"/></div>
        {data.ats_score === null ? (
          <div className="ats-empty-state">
            <span className="ats-empty-icon"><ScanSearch size={26}/></span>
            <div>
              <strong>Skor bekleniyor</strong>
              <p>İlk CV analizini çalıştırdığında hazırlık skorun burada görünecek.</p>
            </div>
          </div>
        ) : (
          <div><div className="flex items-end gap-2"><strong className="text-[clamp(4.5rem,7vw,6.4rem)] font-black leading-none tracking-[-.06em] text-white">{data.ats_score}</strong><span className="mb-3 text-sm text-[#60646d]">/100</span></div><div className="mt-7 h-px bg-white/[.08]"><div className="line-grow h-px bg-[#9b8afb]" style={{width:`${Math.min(data.ats_score,100)}%`}}/></div></div>
        )}
        <Link href="/ats-demo" className="flex items-center justify-between border-t border-white/[.08] pt-5 text-xs font-semibold text-[#aeb1b8] hover:text-white">Analizi incele<ArrowUpRight size={16}/></Link>
      </article>
    </section>

    <section className="mt-5 grid gap-5 sm:grid-cols-3">
      <Metric label="Aktif başvuru" value={data.active_applications_count} icon={<Briefcase size={17}/>}/>
      <Metric label="CV versiyonu" value={data.cv_version_count} icon={<FileText size={17}/>}/>
      <Metric label="Profil tamamlanma" value={`${data.profile_completion_percentage}%`} icon={<Check size={17}/>}/>
    </section>

    <section className="mt-5 grid gap-5 xl:grid-cols-[.9fr_1.1fr]">
      <article className="executive-card p-6 sm:p-8">
        <div className="mb-7 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-white">Başvurularına genel bakış</h2><p className="mt-1 text-xs text-[#9097ae]">Süreç dağılımı</p></div><Link href="/applications" aria-label="Başvuruları aç" className="grid size-10 place-items-center rounded-[9px] bg-white/[.05] text-[#8b8f98] hover:bg-white/[.09] hover:text-white"><ArrowUpRight size={16}/></Link></div>
        {Object.keys(data.status_distribution).length ? <div className="space-y-6">{Object.entries(data.status_distribution).map(([s,c])=>{const p=Math.round(c/Math.max(data.active_applications_count,1)*100);return <div key={s}><div className="mb-2 flex justify-between text-xs"><span className="font-medium text-[#aeb1b8]">{LABELS[s]??s}</span><span className="font-mono text-[#666a73]">{c} / %{p}</span></div><div className="h-px bg-white/[.08]"><div className="h-px bg-[#ae9eff]" style={{width:`${p}%`}}/></div></div>})}</div> : <Empty text="Henüz başvuru verisi yok." href="/applications" action="İlk başvuruyu ekle"/>}
      </article>
      <article className="executive-card p-6 sm:p-8">
        <div className="mb-7 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-white">Yaklaşan mülakatlar</h2><p className="mt-1 text-xs text-[#9097ae]">Hazırlık takvimi</p></div><Video size={17} className="text-[#c4b8ff]"/></div>
        {data.upcoming_interviews.length ? data.upcoming_interviews.map((it,i)=><div key={`${it.company}-${i}`} className="flex flex-col gap-4 border-t border-white/[.08] py-5 first:border-0 first:pt-0 sm:flex-row sm:items-center"><div className="grid size-10 place-items-center rounded-[9px] bg-[#262a3d] text-xs font-semibold text-white">{it.company[0]}</div><div className="flex-1"><p className="text-sm font-semibold text-white">{it.company}</p><p className="mt-1 text-xs text-[#949cb2]">{it.position}</p></div><Link href="/interview-room-demo" className="flex min-h-10 items-center justify-center gap-2 rounded-[9px] border border-white/[.1] px-4 text-xs font-semibold text-[#b7bac1] hover:bg-white hover:text-[#10121c]">Hazırlan<ArrowRight size={14}/></Link></div>) : <Empty text="Takvimde yaklaşan mülakat yok." href="/interview-prep-demo" action="Pratik başlat"/>}
      </article>
    </section>
  </div>;
}

function Metric({label,value,icon}:{label:string;value:string|number;icon:React.ReactNode}){return <article className="executive-card precision-hover flex min-h-36 flex-col justify-between p-5"><div className="flex items-center justify-between"><span className="micro-label text-[#929ab1]">{label}</span><span className="text-[#c4b8ff]">{icon}</span></div><strong className="text-4xl font-bold tracking-[-.04em] text-white">{value}</strong></article>}
function Empty({text,href,action}:{text:string;href:string;action:string}){return <div className="flex min-h-40 flex-col items-start justify-end border-t border-white/[.08] pt-5"><p className="text-xs text-[#949cb2]">{text}</p><Link href={href} className="mt-4 flex items-center gap-2 text-xs font-semibold text-[#c4b8ff] hover:gap-3 hover:text-white">{action}<ArrowRight size={14}/></Link></div>}
function Skeleton(){return <div className="mx-auto max-w-[1520px] animate-pulse px-5 py-10 sm:px-8 lg:px-10"><div className="h-24 max-w-2xl rounded-[14px] bg-white/[.05]"/><div className="mt-10 grid gap-5 xl:grid-cols-[1.35fr_.65fr]"><div className="h-[390px] rounded-[14px] bg-white/[.05]"/><div className="h-[390px] rounded-[14px] bg-white/[.05]"/></div></div>}
