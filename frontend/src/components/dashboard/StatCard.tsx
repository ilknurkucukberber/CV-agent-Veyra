import { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  description?: string;
}

export default function StatCard({ title, value, icon, description }: StatCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col justify-between h-full min-h-[140px]">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-gray-500 dark:text-gray-400 text-sm font-medium">{title}</p>
          <h3 className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{value}</h3>
        </div>
        <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
          {icon}
        </div>
      </div>
      {description && (
        <p className="text-sm text-gray-400 mt-4">{description}</p>
      )}
    </div>
  );
}
