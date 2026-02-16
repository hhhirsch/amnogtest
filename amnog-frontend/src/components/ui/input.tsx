import { cn } from "@/lib/utils";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "bg-bg2 border border-white/[0.13] rounded-[10px] px-4 py-3 text-sm text-ink font-sans outline-none w-full transition-all duration-200",
        "focus:border-gold focus:bg-[#1c2133] focus:ring-2 focus:ring-gold/20",
        "placeholder:text-ink-muted",
        // Ensure text remains readable in all states
        "[color-scheme:dark]",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        // Fix autofill styles for dark theme
        "autofill:[-webkit-text-fill-color:#e2e8f0]",
        "autofill:[-webkit-box-shadow:0_0_0px_1000px_#1c2133_inset]",
        "autofill:[transition:background-color_5000s_ease-in-out_0s]"
      )}
      {...props}
    />
  );
}
