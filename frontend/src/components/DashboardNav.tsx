"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { staticArchive } from "@/lib/archive";

const sections = [
  ["/", "Dashboard"],
  ["/models", "Cars"],
  ["/teams", "Teams"],
  ["/upgrades", "Upgrades"],
  ["/compare", "Compare"],
  ["/performance", "Performance"],
  ["/evidence", "Evidence"],
  ["/analyze", "Analyze"],
];

export default function DashboardNav() {
  const pathname = usePathname().replace(/\/$/, "") || "/";
  return (
    <>
      <a className="d-skip" href="#main-content">
        Skip to content
      </a>
      <header className="d-header">
        <Link href="/" className="site-logo" aria-label="Form & Flow dashboard">
          <span className="logo-lines">{"///"}</span> FORM & FLOW
          <small>F1 ENGINEERING</small>
        </Link>
        <div className="d-header-meta">
          <span className="d-season">
            <i /> 2026 SEASON
          </span>
          <Link href="/about">About</Link>
          {!staticArchive && <Link href="/review">Review studio ↗</Link>}
        </div>
      </header>
      <nav className="d-nav" aria-label="Main navigation">
        {sections.map(([href, label], index) => (
          <Link
            key={href}
            href={href}
            aria-current={pathname === href ? "page" : undefined}
          >
            {index === 0 && (
              <span className="d-nav-symbol" aria-hidden="true">
                ▦
              </span>
            )}
            {label}
          </Link>
        ))}
      </nav>
    </>
  );
}
