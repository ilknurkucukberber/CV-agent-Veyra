import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Application, ApplicationUpdate } from '@/types/application';
import { X, Calendar, AlignLeft, MessageSquare, Sparkles } from 'lucide-react';

interface ApplicationModalProps {
  application: Application | null;
  onClose: () => void;
  onSave: (id: number, data: ApplicationUpdate) => Promise<void>;
  onGenerateChecklist: (id: number) => Promise<any>;
}

export default function ApplicationModal({ application, onClose, onSave, onGenerateChecklist }: ApplicationModalProps) {
  const [notes, setNotes] = useState(application?.notes || '');
  const [interviewNotes, setInterviewNotes] = useState(application?.interview_notes || '');
  const [interviewAt, setInterviewAt] = useState(
    application?.interview_at ? application.interview_at.slice(0, 16) : '',
  );
  const [checklist, setChecklist] = useState<any[]>([]);
  const [loadingChecklist, setLoadingChecklist] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!application) return null;

  const handleSave = async () => {
    await onSave(application.id, {
      notes,
      interview_notes: interviewNotes,
      interview_at: interviewAt ? new Date(interviewAt).toISOString() : null,
    });
  };

  const generateChecklist = async () => {
    setLoadingChecklist(true);
    setError(null);
    try {
      const data = await onGenerateChecklist(application.id);
      if (data && data.questions) {
        setChecklist(data.questions);
      }
    } catch (err: any) {
      setError(err.message || 'Mülakat hazırlık listesi üretilirken hata oluştu.');
    } finally {
      setLoadingChecklist(false);
    }
  };

  const modalContent = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-2xl max-h-[90vh] flex flex-col rounded-2xl border border-white/10 bg-[#171a29] shadow-2xl animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-start justify-between border-b border-white/10 p-6">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {application.position} <span className="font-medium text-[#a0a6bc]">@ {application.company}</span>
            </h2>
            <div className="mt-2 flex items-center gap-3">
              <span className="rounded-full bg-[#9b8afb]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#9b8afb] border border-[#9b8afb]/20">
                {application.status}
              </span>
              {application.applied_at && (
                <span className="text-xs font-medium text-[#9097ae]">
                  Başvuru: {new Date(application.applied_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="grid size-8 shrink-0 place-items-center rounded-lg text-[#a0a6bc] hover:bg-white/5 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-[#a0a6bc]">
              <Calendar size={14} /> Görüşme Tarihi <span className="text-white/30 font-normal">(İsteğe bağlı)</span>
            </label>
            <input
              type="datetime-local"
              value={interviewAt}
              onChange={(e) => setInterviewAt(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/50 p-2.5 text-sm text-white placeholder-white/20 focus:border-[#c4b8ff] focus:outline-none focus:ring-1 focus:ring-[#c4b8ff] transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-[#a0a6bc]">
              <AlignLeft size={14} /> Genel Notlar
            </label>
            <textarea 
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/50 p-3 text-sm text-white placeholder-white/20 focus:border-[#c4b8ff] focus:outline-none focus:ring-1 focus:ring-[#c4b8ff] transition-colors min-h-[80px]"
              placeholder="Fırsat ile ilgili aldığınız kısa notlar..."
            />
          </div>

          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-[#a0a6bc]">
              <MessageSquare size={14} /> Mülakat Notları
            </label>
            <textarea 
              value={interviewNotes}
              onChange={(e) => setInterviewNotes(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/50 p-3 text-sm text-white placeholder-white/20 focus:border-[#c4b8ff] focus:outline-none focus:ring-1 focus:ring-[#c4b8ff] transition-colors min-h-[80px]"
              placeholder="Mülakat sırasında veya sonrasında aldığınız detaylı notlar..."
            />
          </div>

          <div className="flex justify-end pt-2">
            <button 
              onClick={handleSave} 
              className="rounded-xl bg-[#9b8afb] px-5 py-2.5 text-sm font-bold text-black hover:bg-[#c4b8ff] transition-colors shadow-[0_0_15px_rgba(155,138,251,0.3)]"
            >
              Değişiklikleri Kaydet
            </button>
          </div>

          <div className="border-t border-white/10 pt-6 mt-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sparkles size={16} className="text-[#9b8afb]" />
                  AI Mülakat Hazırlık (Prep-Checklist)
                </h3>
                {!application.resume_version_id && (
                  <p className="text-[11px] text-[#ffb86c] mt-1">
                    Uyarı: Hazırlık listesi üretmek için bu başvuruya bir CV versiyonu bağlanmış olmalıdır.
                  </p>
                )}
              </div>
              <button 
                onClick={generateChecklist} 
                disabled={loadingChecklist || !application.resume_version_id}
                className="rounded-lg bg-white/5 border border-white/10 px-4 py-2 text-xs font-semibold text-white hover:bg-white/10 hover:border-white/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loadingChecklist ? (
                  <>
                    <div className="size-3.5 border-2 border-t-transparent border-white rounded-full animate-spin"></div>
                    Üretiliyor...
                  </>
                ) : (
                  'Liste Üret'
                )}
              </button>
            </div>
            
            {error && <p className="text-xs text-[#ff5555] mb-4 bg-[#ff5555]/10 border border-[#ff5555]/20 p-2.5 rounded-lg">{error}</p>}

            {checklist.length > 0 && (
              <div className="space-y-3">
                {checklist.map((item, idx) => (
                  <div key={idx} className="p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                    <p className="text-sm font-medium text-white leading-relaxed">{item.question}</p>
                    <div className="flex space-x-2 mt-3">
                      <span className="text-[10px] font-semibold px-2 py-1 bg-[#8be9fd]/10 text-[#8be9fd] rounded-md border border-[#8be9fd]/20">
                        {item.category}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-1 bg-[#50fa7b]/10 text-[#50fa7b] rounded-md border border-[#50fa7b]/20">
                        {item.source}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );

  if (typeof document !== 'undefined') {
    return createPortal(modalContent, document.body);
  }
  return null;
}
