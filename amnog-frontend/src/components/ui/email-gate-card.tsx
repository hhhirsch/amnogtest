import { ReactNode } from "react";
import { Mail } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EmailGateCardProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

export function EmailGateCard({ 
  title = "Fast geschafft!", 
  description, 
  children,
  className 
}: EmailGateCardProps) {
  return (
    <div className={cn(
      "bg-surface border border-white/[0.13] rounded-[20px] p-8 shadow-[0_24px_64px_rgba(0,0,0,0.5)] relative overflow-hidden",
      className
    )}>
      {/* Gold top-line gradient */}
      <div className="absolute h-0.5 inset-x-0 top-0 bg-gradient-to-r from-transparent via-gold to-transparent opacity-60" />
      
      {/* Icon box */}
      <div className="w-12 h-12 rounded-xl bg-gold/10 border border-gold/25 flex items-center justify-center mb-4">
        <Mail className="w-6 h-6 text-gold" />
      </div>
      
      {/* Title */}
      <h1 className="font-serif text-[28px] text-ink leading-snug mb-2">{title}</h1>
      
      {/* Description */}
      {description && (
        <p className="text-sm text-ink-soft font-light leading-relaxed mb-6">
          {description}
        </p>
      )}
      
      {children}
    </div>
  );
}
