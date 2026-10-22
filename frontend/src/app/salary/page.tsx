'use client';

import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import SalaryResultCard from '@/components/SalaryResultCard';
import { API_BASE, getToken } from '@/lib/api';
import ToolPageShell from '@/components/ToolPageShell';

export default function SalaryAnalysisPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    position: '',
    city: '',
    experience_level: 'mid',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/salary/estimate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify({
          position: formData.position,
          city: formData.city,
          experience_level: formData.experience_level,
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Bir hata oluştu');
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ToolPageShell index="09" title="Maaş Analizi" description="Rol, şehir ve deneyim seviyene göre piyasa aralığını değerlendir; teklif görüşmesine veriyle hazırlan.">
      <div className="mx-auto max-w-4xl space-y-8">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Pozisyon <span className="text-red-500">*</span></label>
              <input 
                required
                type="text"
                placeholder="Örn: Yazılım Mühendisi, Product Manager"
                className="w-full p-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.position}
                onChange={e => setFormData({...formData, position: e.target.value})}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Şehir <span className="text-red-500">*</span></label>
              <input 
                required
                type="text"
                placeholder="Örn: İstanbul, Remote"
                className="w-full p-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.city}
                onChange={e => setFormData({...formData, city: e.target.value})}
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Deneyim Seviyesi <span className="text-red-500">*</span></label>
              <select 
                className="w-full p-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.experience_level}
                onChange={e => setFormData({...formData, experience_level: e.target.value})}
              >
                <option value="junior">Junior (0-2 Yıl)</option>
                <option value="mid">Mid (3-5 Yıl)</option>
                <option value="senior">Senior (5+ Yıl)</option>
              </select>
            </div>
          </div>
          
          <button 
            type="submit" 
            disabled={loading}
            className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Hesaplanıyor...' : 'Maaş Tahmini Al'}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/30 text-red-800 dark:text-red-400 rounded-lg flex items-start border border-red-200 dark:border-red-800">
          <AlertCircle className="mr-3 flex-shrink-0 mt-0.5" size={20} />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="mt-8 transition-all duration-500">
          <SalaryResultCard result={result} />
        </div>
      )}
      </div>
    </ToolPageShell>
  );
}
