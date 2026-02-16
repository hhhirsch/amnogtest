"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface AccordionProps {
  title: string;
  showBadge?: boolean;
  badgeText?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function Accordion({ 
  title, 
  showBadge = false, 
  badgeText = "MVP", 
  children, 
  defaultOpen = false 
}: AccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="bg-surface border border-white/[0.13] rounded-[14px] overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer select-none"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="text-[13px] font-medium text-ink-soft flex items-center gap-2.5">
          <span>{title}</span>
          {showBadge && (
            <span className="text-[9px] font-semibold tracking-[0.1em] uppercase bg-gold/10 text-gold border border-gold/30 rounded px-1.5 py-0.5">
              {badgeText}
            </span>
          )}
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-ink-soft transition-transform duration-250",
            isOpen && "rotate-180"
          )}
        />
      </div>

      {/* Body */}
      {isOpen && (
        <div className="text-[13px] text-ink-muted leading-relaxed px-5 pb-4 border-t border-white/[0.07]">
          {children}
        </div>
      )}
    </div>
  );
}
