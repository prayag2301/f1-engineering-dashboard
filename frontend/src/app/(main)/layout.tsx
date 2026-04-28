import type { ReactNode } from "react";
import Link from "next/link";

export default function MainLayout({ children }: { children: ReactNode }) {
  return (
    <div className="container">
      <header className="header">
        <Link href="/" className="header__logo">
          F1 // Engineering
        </Link>
        <nav className="header__nav">
          <Link href="/">Cars</Link>
          <Link href="/teams">Teams</Link>
          <Link href="/performance">Performance</Link>
          <Link href="/evidence">Evidence</Link>
          <Link href="/analyze">Analyze</Link>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
