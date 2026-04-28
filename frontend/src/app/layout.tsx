import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "PropFinder — Distressed Deals",
  description: "Montgomery County distressed real estate investment opportunities",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 h-screen overflow-hidden">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
