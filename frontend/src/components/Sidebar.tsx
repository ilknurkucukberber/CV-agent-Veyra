'use client';

import Link from 'next/link';
import Brand from './Brand';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, FileText, Target, PenTool, Video, Map, Briefcase, Menu, X, Calculator, Contact2, LogOut, UserCog, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getCurrentUser, logout } from '@/lib/auth';

const NAV_ITEMS = [
  { name: 'Genel Bakış', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Profil', href: '/profile', icon: UserCog },
  { name: 'CV Analizi', href: '/ats-demo', icon: FileText },
  { name: 'İş Eşleşmesi', href: '/job-match-demo', icon: Target },
  { name: 'CV Editör', href: '/cv-editor', icon: PenTool },
  { name: 'Mülakat', href: '/interview-prep-demo', icon: Video },
  { name: 'Kariyer Rotası', href: '/career-roadmap-demo', icon: Map },
  { name: 'LinkedIn', href: '/linkedin', icon: Contact2 },
  { name: 'Başvurular', href: '/applications', icon: Briefcase },
  { name: 'Maaş Analizi', href: '/salary', icon: Calculator },
];

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
}

export default function Sidebar({ isCollapsed = false, setIsCollapsed }: { isCollapsed?: boolean; setIsCollapsed?: (val: boolean) => void }) {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [displayName, setDisplayName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCurrentUser()
      .then((user) => {
        if (!cancelled) setDisplayName(user.full_name?.trim() || user.email);
      })
      .catch(() => {
        if (!cancelled) setDisplayName(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <>
    <button onClick={() => setIsOpen(!isOpen)} aria-label={isOpen ? 'Menüyü kapat' : 'Menüyü aç'}
      className="fixed left-4 top-4 z-50 grid size-11 place-items-center rounded-xl border border-white/10 bg-[#171a29] text-white lg:hidden">
      {isOpen ? <X size={19} /> : <Menu size={19} />}
    </button>
    {isOpen && <button aria-label="Menüyü kapat" onClick={() => setIsOpen(false)} className="fixed inset-0 z-30 cursor-default bg-black/70 backdrop-blur-sm lg:hidden" />}
    <aside className={`premium-sidebar fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/[.08] bg-[#121521]/95 py-5 backdrop-blur-xl transition-all duration-300 ease-out ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'} ${isCollapsed ? 'w-[88px] px-3' : 'w-[272px] px-4'}`}>
      
      <div className={`mb-8 flex ${isCollapsed ? 'flex-col items-center gap-6 mt-1' : 'items-center justify-between pl-1 pr-1'}`}>
        <Link href="/dashboard" onClick={() => setIsOpen(false)} aria-label="Veyra genel bakış" className="flex items-center gap-2 py-1 min-w-0">
          <Brand compact={isCollapsed} />
        </Link>
        <button 
          onClick={() => setIsCollapsed?.(!isCollapsed)}
          className="hidden lg:flex h-[28px] w-[28px] shrink-0 items-center justify-center rounded-[8px] bg-transparent text-[#9097ae] hover:bg-white/[.06] hover:text-white transition-colors"
          title={isCollapsed ? "Menüyü genişlet" : "Menüyü daralt"}
        >
          {isCollapsed ? <PanelLeftOpen size={18} strokeWidth={1.8} /> : <PanelLeftClose size={18} strokeWidth={1.8} />}
        </button>
      </div>
      
      {isCollapsed ? (
        <div className="mb-5 border-y border-white/[.08] py-4 flex justify-center transition-all duration-300">
           <i className="status-pulse size-2 rounded-full bg-[#9b8afb]" title="Çalışma alanı aktif" />
        </div>
      ) : (
        <div className="mb-5 border-y border-white/[.08] py-4 transition-all duration-300">
          <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-[.13em] text-[#777b85]"><span>Çalışma alanın</span><span className="flex items-center gap-2 text-[#b8bbc2]"><i className="status-pulse size-1.5 rounded-full bg-[#9b8afb]" />Aktif</span></div>
        </div>
      )}
      
      <nav aria-label="Ana menü" className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return <Link key={item.href} href={item.href} onClick={() => setIsOpen(false)}
            title={isCollapsed ? item.name : undefined}
            aria-current={active ? "page" : undefined}
            className={`premium-nav-link group flex min-h-11 items-center rounded-[10px] text-[13px] font-medium transition-all duration-300 ${isCollapsed ? 'justify-center px-0' : 'gap-3 px-3'} ${active ? 'is-active bg-[#262a3d] text-white' : 'text-[#a0a6bc] hover:bg-white/[.04] hover:text-white'}`}>
            <Icon size={isCollapsed ? 18 : 16} strokeWidth={1.7} className={`shrink-0 transition-all duration-300 ${active ? 'text-[#c4b8ff]' : 'text-[#929ab1] group-hover:text-[#aeb1b8]'}`} />
            <span className={`transition-all duration-300 overflow-hidden whitespace-nowrap ${isCollapsed ? 'w-0 opacity-0' : 'w-full opacity-100'}`}>{item.name}</span>
            {active && !isCollapsed && <span className="h-4 w-[2px] rounded-full bg-[#ae9eff] shadow-[0_0_14px_#9b8afb] shrink-0" />}
          </Link>;
        })}
      </nav>
      
      <div className="mt-4 border-t border-white/[.08] pt-4">
        <div className={`flex items-center ${isCollapsed ? 'justify-center flex-col gap-2' : 'gap-3'}`}>
          <div className="grid size-9 shrink-0 place-items-center rounded-[9px] bg-[#262a3d] text-xs font-semibold text-white cursor-help" title={isCollapsed ? (displayName ?? "Kariyer Adayı") : undefined}>{initialsOf(displayName ?? "Kariyer Adayı")}</div>
          <div className={`transition-all duration-300 overflow-hidden whitespace-nowrap ${isCollapsed ? 'w-0 h-0 opacity-0' : 'min-w-0 flex-1 opacity-100'}`}><p className="truncate text-xs font-semibold text-white">{displayName ?? "Kariyer Adayı"}</p><p className="mt-1 text-[10px] text-[#9097ae]">Güvenli oturum</p></div>
          <button onClick={logout} title={isCollapsed ? "Çıkış yap" : undefined} aria-label="Çıkış yap" className={`grid shrink-0 place-items-center rounded-[10px] text-[#9ba2b7] hover:bg-white/[.05] hover:text-white transition-all duration-300 ${isCollapsed ? 'size-9 mt-1' : 'size-10'}`}><LogOut size={16} /></button>
        </div>
      </div>
    </aside>
  </>;
}
