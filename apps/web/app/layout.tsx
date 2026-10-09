import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Newsreader, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";

import "./globals.css";

const editorial = Newsreader({
  subsets: ["latin"],
  weight: ["400", "600"],
  style: "normal",
  display: "swap",
  variable: "--font-editorial",
});
const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: "normal",
  display: "swap",
  variable: "--font-interface",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: "400",
  style: "normal",
  display: "swap",
  preload: false,
  variable: "--font-technical",
});

export const metadata: Metadata = {
  title: "CausalBio Lab — Investigate biological mechanisms",
  description:
    "Build evidence-backed maps from biological questions to tissues, pathways, interventions, and uncertainty.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light dark",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${editorial.variable} ${sans.variable} ${mono.variable}`}>{children}</body>
    </html>
  );
}
