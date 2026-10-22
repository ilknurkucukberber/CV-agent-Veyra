'use client';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Building2, Briefcase } from 'lucide-react';
import KanbanBoard from '@/components/applications/KanbanBoard';
import FunnelSummary from '@/components/applications/FunnelSummary';
import { Application, ApplicationStatus, ApplicationUpdate } from '@/types/application';
import { API_BASE, getToken } from '@/lib/api';
import ToolPageShell from '@/components/ToolPageShell';

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newCompany, setNewCompany] = useState('');
  const [newPosition, setNewPosition] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const fetchApplications = async () => {
    try {
      const res = await fetch(`${API_BASE}/applications`, {
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setApplications(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const handleStatusChange = async (id: number, newStatus: ApplicationStatus) => {
    // Optimistic update
    setApplications(prev => prev.map(app => app.id === id ? { ...app, status: newStatus } : app));
    
    try {
      await fetch(`${API_BASE}/applications/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch (e) {
      console.error(e);
      // Revert if error
      fetchApplications();
    }
  };

  const handleUpdateApplication = async (id: number, data: ApplicationUpdate) => {
    try {
      const res = await fetch(`${API_BASE}/applications/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const updated = await res.json();
        setApplications(prev => prev.map(app => app.id === id ? updated : app));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerateChecklist = async (id: number) => {
    const res = await fetch(`${API_BASE}/applications/${id}/prep-checklist`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Bir hata oluştu');
    }
    return await res.json();
  };

  const handleCreateNew = () => {
    setNewCompany('');
    setNewPosition('');
    setIsCreateModalOpen(true);
  };

  const submitNewApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompany || !newPosition) return;
    setIsCreating(true);

    try {
      const res = await fetch(`${API_BASE}/applications`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify({ company: newCompany, position: newPosition, status: 'saved' }),
      });
      if (res.ok) {
        const newApp = await res.json();
        setApplications(prev => [...prev, newApp]);
        setIsCreateModalOpen(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsCreating(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-900 dark:text-white">Yükleniyor...</div>;
  }

  return (
    <ToolPageShell index="08" title="Başvuru Portföyü" description="Tüm fırsatlarını tek akışta yönet; süreçleri, görüşmeleri ve sonraki aksiyonları kontrol altında tut." wide>
      <div className="applications-stage">
      <header className="applications-toolbar">
        <span className="micro-label text-[#70cfc6]">CANLI SÜREÇ PANOSU</span>
        <button 
          onClick={handleCreateNew}
          className="tool-primary-action"
        >
          + Yeni Başvuru Ekle
        </button>
      </header>

      <FunnelSummary />

      <div className="applications-board">
        <KanbanBoard 
          applications={applications} 
          onStatusChange={handleStatusChange} 
          onUpdateApplication={handleUpdateApplication}
          onGenerateChecklist={handleGenerateChecklist}
        />
      </div>

      {isCreateModalOpen && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#171a29] p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-white">Yeni Başvuru Ekle</h3>
                <p className="text-xs text-[#a0a6bc] mt-1">Sürecini takip etmek istediğin fırsatı gir.</p>
              </div>
              <button 
                onClick={() => setIsCreateModalOpen(false)}
                className="grid size-8 place-items-center rounded-lg text-[#a0a6bc] hover:bg-white/5 hover:text-white transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            
            <form onSubmit={submitNewApplication} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#a0a6bc]">Şirket Adı</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[#a0a6bc]">
                    <Building2 size={16} />
                  </div>
                  <input 
                    type="text" 
                    required 
                    autoFocus
                    value={newCompany}
                    onChange={(e) => setNewCompany(e.target.value)}
                    className="block w-full rounded-xl border border-white/10 bg-black/50 py-2.5 pl-10 pr-3 text-sm text-white placeholder-white/20 focus:border-[#c4b8ff] focus:outline-none focus:ring-1 focus:ring-[#c4b8ff] transition-colors"
                    placeholder="Örn: Google, Meta..."
                  />
                </div>
              </div>
              
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#a0a6bc]">Pozisyon</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[#a0a6bc]">
                    <Briefcase size={16} />
                  </div>
                  <input 
                    type="text" 
                    required 
                    value={newPosition}
                    onChange={(e) => setNewPosition(e.target.value)}
                    className="block w-full rounded-xl border border-white/10 bg-black/50 py-2.5 pl-10 pr-3 text-sm text-white placeholder-white/20 focus:border-[#c4b8ff] focus:outline-none focus:ring-1 focus:ring-[#c4b8ff] transition-colors"
                    placeholder="Örn: Senior Frontend Developer"
                  />
                </div>
              </div>
              
              <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-white/10">
                <button 
                  type="button" 
                  onClick={() => setIsCreateModalOpen(false)}
                  className="rounded-xl px-4 py-2 text-sm font-medium text-white hover:bg-white/5 transition-colors"
                >
                  İptal
                </button>
                <button 
                  type="submit" 
                  disabled={isCreating}
                  className="rounded-xl bg-[#9b8afb] px-5 py-2 text-sm font-bold text-black hover:bg-[#c4b8ff] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? 'Ekleniyor...' : 'Başvuruyu Ekle'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

    </div>
    </ToolPageShell>
  );
}
