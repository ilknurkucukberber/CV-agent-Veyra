import { ArrowUpRight, Check, FileText, Sparkles, Target } from "lucide-react";

/** A decorative product illustration; it does not display account or analysis data. */
export default function CareerCanvas() {
  return <div className="career-canvas" aria-hidden="true">
    <div className="career-canvas-top"><span>HER ADIMDA BİRAZ DAHA İLERİ</span><ArrowUpRight size={16} /></div>
    <div className="career-canvas-flow">
      <span className="career-step"><FileText size={18} /><span>Deneyimin<small>Hikâyeni görünür kıl</small></span><Check size={14} /></span>
      <span className="career-connector" />
      <span className="career-step career-step-focus"><Sparkles size={18} /><span>Potansiyelin<small>Güçlü yönlerini keşfet</small></span><span className="career-dot" /></span>
      <span className="career-connector" />
      <span className="career-step"><Target size={18} /><span>Bir sonraki fırsatın<small>Hazırlıklı bir adım at</small></span><ArrowUpRight size={14} /></span>
    </div>
    <span className="career-canvas-note">DENEYİMDEN FIRSATA <span>↗</span></span>
  </div>;
}
