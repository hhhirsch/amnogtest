import { cn } from "@/lib/utils";

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "bg-bg2 border border-white/[0.13] rounded-[10px] px-4 py-3 text-sm text-ink font-sans outline-none w-full transition-all duration-200",
        "focus:border-gold focus:bg-[#1c2133] focus:ring-2 focus:ring-gold/20",
        "placeholder:text-ink-muted",
        "resize-none min-h-[88px] leading-relaxed"
      )}
      {...props}
    />
  );
}
