import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "AMNOG Comparator Shortlist",
  description: "Wizard und Ergebnisansicht für AMNOG Comparator Shortlist",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body>
        <main className="mx-auto min-h-screen w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
