import React from 'react';

export default function ScoreGauge({ score }: { score: number | null }) {
  if (score === null) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 h-full min-h-[220px]">
        <h3 className="text-gray-500 font-medium mb-4">Son ATS Skoru</h3>
        <p className="text-gray-400 italic">Henüz analiz bulunmuyor</p>
      </div>
    );
  }

  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  
  let colorClass = "text-red-500";
  if (score >= 70) colorClass = "text-yellow-500";
  if (score >= 85) colorClass = "text-green-500";

  return (
    <div className="flex flex-col items-center justify-center p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 h-full min-h-[220px]">
      <h3 className="text-gray-700 dark:text-gray-300 font-medium mb-4">Son ATS Skoru</h3>
      
      <div className="relative flex items-center justify-center">
        <svg className="transform -rotate-90 w-32 h-32">
          <circle 
            cx="64" cy="64" r={radius}
            stroke="currentColor" 
            strokeWidth="10" 
            fill="transparent" 
            className="text-gray-200 dark:text-gray-700" 
          />
          <circle 
            cx="64" cy="64" r={radius} 
            stroke="currentColor" 
            strokeWidth="10" 
            fill="transparent" 
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={`${colorClass} transition-all duration-1000 ease-out`} 
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className="text-3xl font-bold dark:text-white">{score}</span>
          <span className="text-xs text-gray-500">/ 100</span>
        </div>
      </div>
    </div>
  );
}
