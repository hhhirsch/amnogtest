import { cn } from "@/lib/utils";

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "bg-[#1c2133] border border-white/[0.13] rounded-[10px] px-4 py-3 text-sm text-ink font-sans outline-none w-full transition-all duration-200",
        "hover:border-white/[0.2]",
        "focus:border-gold focus:ring-2 focus:ring-gold/20",
        "placeholder:text-ink-muted",
        "resize-none min-h-[88px] leading-relaxed",
        // Ensure text remains readable in all states
        "[color-scheme:dark]",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
      {...props}
    />
  );
}
