"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { staticArchive } from "@/lib/archive";

// Each tab owns a group of routes; tabs with more than one page show sub-tabs.
const sections: { label: string; pages: [string, string][] }[] = [
  { label: "Race Week", pages: [["/", "Race Week"]] },
  {
    label: "Cars",
    pages: [
      ["/models", "3D explorer"],
      ["/teams", "All teams"],
    ],
  },
  { label: "Compare", pages: [["/compare", "Compare"]] },
  {
    label: "Development",
    pages: [
      ["/upgrades", "Change log"],
      ["/performance", "Performance"],
      ["/evidence", "Sources"],
      ["/analyze", "Analyze"],
    ],
  },
];

export default function DashboardNav() {
  const pathname = usePathname().replace(/\/$/, "") || "/";
  const current =
    sections.find((s) =>
      s.pages.some(([href]) => href !== "/" && pathname.startsWith(href)),
    ) ??
    (pathname.startsWith("/car/")
      ? sections[1]
      : pathname === "/"
        ? sections[0]
        : undefined);
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
        {sections.map((section) => (
          <Link
            key={section.label}
            href={section.pages[0][0]}
            aria-current={section === current ? "page" : undefined}
          >
            {section.label}
          </Link>
        ))}
      </nav>
      {current && current.pages.length > 1 && (
        <nav className="d-subnav" aria-label={`${current.label} pages`}>
          {current.pages.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>
      )}
    </>
  );
}
