import type { Metadata } from "next";
import { Toaster } from "sonner";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AMNOG Comparator Shortlist",
  description: "Wizard und Ergebnisansicht für AMNOG Comparator Shortlist",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-bg text-ink font-sans min-h-screen">
        <main className="mx-auto min-h-screen w-full max-w-4xl p-6">{children}</main>
        <Toaster richColors position="top-right" />
        <Analytics />
      </body>
    </html>
  );
}
