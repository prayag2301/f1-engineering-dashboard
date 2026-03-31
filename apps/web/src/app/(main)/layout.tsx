import type { ReactNode } from "react";

export default function MainLayout({ children }: { children: ReactNode }) {
  return (
    <div className="container">
      <header className="header">
        <a href="/" className="header__logo">
          F1 // Engineering
        </a>
        <nav className="header__nav">
          <a href="/">Cars</a>
          <a href="/teams">Teams</a>
          <a href="/performance">Performance</a>
          <a href="/evidence">Evidence</a>
          <a href="/analyze">Analyze</a>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
