"use client";

import { usePathname } from "next/navigation";
import Sidebar from "./Sidebar";
import AuthGuard from "./AuthGuard";
import { useState, useEffect } from "react";

const PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password", "/verify-email"];
const PUBLIC_PATH_PREFIXES = ["/share/"];

function isPublicPath(pathname: string): boolean {
  return (
    PUBLIC_PATHS.includes(pathname) ||
    PUBLIC_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix))
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("sidebar_collapsed");
    if (stored) setIsCollapsed(JSON.parse(stored));
  }, []);

  const handleCollapse = (val: boolean) => {
    setIsCollapsed(val);
    localStorage.setItem("sidebar_collapsed", JSON.stringify(val));
  };

  if (isPublicPath(pathname)) {
    return <div className="min-h-screen app-canvas">{children}</div>;
  }

  return (
    <AuthGuard>
      <div className="app-canvas flex min-h-screen">
        <Sidebar isCollapsed={isCollapsed} setIsCollapsed={handleCollapse} />
        <div className={`app-content flex min-h-screen w-full flex-1 flex-col pt-16 lg:pt-0 transition-all duration-300 ease-out ${isCollapsed ? 'lg:ml-[88px]' : 'lg:ml-[272px]'}`}>
          <main className="flex-1 route-enter">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
