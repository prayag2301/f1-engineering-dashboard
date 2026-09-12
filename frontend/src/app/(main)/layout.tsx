import Link from "next/link";
import { staticArchive } from "@/lib/archive";
import type { ReactNode } from "react";
export default function MainLayout({ children }: { children: ReactNode }) {
  return (
    <div className="container">
      <header className="site-header">
        <Link href="/" className="site-logo">
          <span className="logo-lines">{"///"}</span> FORM & FLOW{" "}
          <small>F1 ENGINEERING</small>
        </Link>
        <nav aria-label="Main navigation">
          <Link href="/">Car archive</Link>
          <Link href="/compare">Compare</Link>
          <Link href={staticArchive ? "/about" : "/review"}>
            {staticArchive ? "About the archive" : "Review studio ↗"}
          </Link>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
