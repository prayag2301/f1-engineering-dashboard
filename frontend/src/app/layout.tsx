import "@/styles/globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "F1 Engineering Dashboard",
  description:
    "The most technically insightful open-source F1 engineering platform. Pure engineering — no drama.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
