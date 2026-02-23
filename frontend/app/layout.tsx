import "@/styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "F1 Engineering Dashboard",
  description:
    "The most technically insightful open-source F1 engineering platform. Pure engineering — no drama.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <header className="header">
            <a href="/" className="header__logo">
              F1 // Engineering
            </a>
            <nav className="header__nav">
              <a href="/">Upgrades</a>
              <a href="/teams">Teams</a>
              <a href="/performance">Performance</a>
            </nav>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
