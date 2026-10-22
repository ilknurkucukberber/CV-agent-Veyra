export default function ProfileProgress({ percentage }: { percentage: number }) {
  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 w-full h-full min-h-[140px] flex flex-col justify-center">
      <div className="flex justify-between items-end mb-2">
        <h3 className="text-gray-700 dark:text-gray-300 font-medium">Profil Tamamlama</h3>
        <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">{percentage}%</span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-4 overflow-hidden">
        <div 
          className="bg-blue-600 h-3 rounded-full transition-all duration-1000 ease-out" 
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Profilini tamamlayarak daha iyi iş eşleşmeleri yakala.
      </p>
    </div>
  );
}
