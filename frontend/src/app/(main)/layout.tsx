import Link from "next/link";
import DashboardNav from "@/components/DashboardNav";
import type { ReactNode } from "react";
export default function MainLayout({ children }: { children: ReactNode }) {
  return (
    <div className="container">
      <DashboardNav />
      <main id="main-content">{children}</main>
      <footer className="d-footer">
        <span>
          FORM & FLOW <span className="d-footer-divider">/</span> F1 Engineering
          Dashboard
        </span>
        <Link href="/about">Public evidence. Visible changes. ↗</Link>
      </footer>
    </div>
  );
}
