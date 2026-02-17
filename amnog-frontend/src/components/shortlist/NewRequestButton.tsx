"use client";

import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";

type NewRequestButtonProps = {
  variant?: "ghost" | "full";
  className?: string;
};

const STORAGE_KEY = "amnog-shortlist-draft";

export function NewRequestButton({ variant = "full", className = "" }: NewRequestButtonProps) {
  const router = useRouter();

  const handleNewRequest = () => {
    if (typeof window === "undefined") return;
    
    // Clear wizard draft from localStorage
    localStorage.removeItem(STORAGE_KEY);
    
    // If already on home page, force reload; otherwise navigate
    if (window.location.pathname === "/") {
      window.location.reload();
    } else {
      router.push("/");
    }
  };

  if (variant === "ghost") {
    return (
      <button
        onClick={handleNewRequest}
        className={`inline-flex items-center gap-1.5 border border-slate-600 bg-transparent text-slate-200 text-[11px] font-semibold rounded-lg px-3.5 py-1.5 hover:bg-slate-800 transition-colors ${className}`}
      >
        <RefreshCw className="h-4 w-4" />
        Neue Anfrage
      </button>
    );
  }

  // variant === "full"
  return (
    <button
      onClick={handleNewRequest}
      className={`inline-flex items-center gap-1.5 bg-gold text-gold-dark text-[11px] font-semibold rounded-lg px-3.5 py-1.5 hover:bg-gold-hover transition-colors ${className}`}
    >
      <RefreshCw className="h-4 w-4" />
      Neue Anfrage
    </button>
  );
}
