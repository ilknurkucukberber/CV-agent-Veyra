import React from 'react';
import { Info, Calendar, Database } from 'lucide-react';

interface SalaryResult {
  range_low: number;
  range_mid: number;
  range_high: number;
  currency: string;
  source: string;
  source_date: string;
  disclaimer: string;
}

export default function SalaryResultCard({ result }: { result: SalaryResult }) {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: result.currency, maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden w-full max-w-3xl mx-auto">
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 p-6 text-white text-center">
        <h3 className="text-xl font-bold mb-1">Tahmini Maaş Aralığı</h3>
        <p className="text-blue-100 text-sm opacity-90">Kriterlerinize uygun yaklaşık iç referans aralığı</p>
      </div>
      
      <div className="p-8">
        <div className="flex flex-col items-center justify-center mb-10">
          <span className="text-4xl font-extrabold text-gray-900 dark:text-white mb-2">
            {formatCurrency(result.range_mid)}
          </span>
          <span className="text-gray-500 dark:text-gray-400 font-medium">Ortalama Beklenti</span>
        </div>

        <div className="relative pt-6 pb-10 px-4 mt-8">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full w-full relative">
            <div className="absolute top-0 left-[20%] right-[20%] h-4 bg-blue-400/50 rounded-full" />
            <div className="absolute top-0 left-[48%] right-[48%] h-4 bg-blue-600 rounded-full" />
            
            <div className="absolute -top-1 left-[20%] w-6 h-6 bg-white border-4 border-blue-400 rounded-full shadow transform -translate-x-1/2" />
            <div className="absolute -top-1 left-[50%] w-6 h-6 bg-white border-4 border-blue-600 rounded-full shadow transform -translate-x-1/2" />
            <div className="absolute -top-1 left-[80%] w-6 h-6 bg-white border-4 border-blue-400 rounded-full shadow transform -translate-x-1/2" />
          </div>
          
          <div className="flex justify-between mt-6 text-sm font-semibold text-gray-700 dark:text-gray-300 relative">
            <div className="absolute left-[20%] transform -translate-x-1/2 flex flex-col items-center">
              <span>{formatCurrency(result.range_low)}</span>
              <span className="text-xs text-gray-400 font-normal mt-1">Minimum</span>
            </div>
            <div className="absolute left-[80%] transform -translate-x-1/2 flex flex-col items-center">
              <span>{formatCurrency(result.range_high)}</span>
              <span className="text-xs text-gray-400 font-normal mt-1">Maksimum</span>
            </div>
          </div>
        </div>
        
        <div className="mt-12 pt-6 border-t border-gray-100 dark:border-gray-700">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg">
            <div className="flex flex-col gap-2 flex-1">
              <div className="flex items-center">
                <Database size={14} className="mr-2 text-blue-500" />
                <span className="font-medium">Kaynak:</span>
                <span className="ml-1 text-gray-700 dark:text-gray-300">{result.source}</span>
              </div>
              <div className="flex items-center">
                <Calendar size={14} className="mr-2 text-blue-500" />
                <span className="font-medium">Tarih:</span>
                <span className="ml-1 text-gray-700 dark:text-gray-300">{result.source_date}</span>
              </div>
            </div>
            
            <div className="flex items-start bg-blue-50 dark:bg-blue-900/20 p-3 rounded text-blue-800 dark:text-blue-300 flex-1">
              <Info size={16} className="mr-2 flex-shrink-0 mt-0.5" />
              <p className="leading-relaxed">{result.disclaimer}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
