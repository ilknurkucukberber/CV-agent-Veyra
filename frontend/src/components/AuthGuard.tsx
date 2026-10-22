"use client";

import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const ready = useRequireAuth();

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-500 dark:text-gray-400">
        Yükleniyor…
      </div>
    );
  }

  return <>{children}</>;
}
