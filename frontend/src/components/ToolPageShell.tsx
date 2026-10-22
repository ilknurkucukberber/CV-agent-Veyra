import type { ReactNode } from "react";

export default function ToolPageShell({
  index,
  title,
  description,
  children,
  wide = false,
}: {
  index: string;
  title: string;
  description: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <main className="tool-page">
      <div className="tool-page-orb" aria-hidden="true" />
      <div className={`tool-page-inner ${wide ? "tool-page-wide" : ""}`}>
        <header className="tool-page-header">
          <div>
            <span className="tool-page-index">{index} / VEYRA</span>
            <h1>{title}</h1>
          </div>
          <p>{description}</p>
        </header>
        <section className="tool-page-content">{children}</section>
      </div>
    </main>
  );
}
