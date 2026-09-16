import "@/styles/studio.css";
import "@/styles/dashboard.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  icons: {
    icon: `${process.env.NEXT_PUBLIC_STATIC_ARCHIVE === "true" ? process.env.NEXT_PUBLIC_BASE_PATH || "" : ""}/icon.svg`,
  },
  title: "Form & Flow — F1 Engineering Dashboard",
  description:
    "Inspect Formula 1 cars, compare upgrades, and understand technical changes through interactive models and public evidence.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
