import { cn } from "@/lib/utils";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "bg-[#1c2133] border border-white/[0.13] rounded-[10px] px-4 py-3 text-sm text-ink font-sans outline-none w-full transition-all duration-200",
        "hover:border-white/[0.2]",
        "focus:border-gold focus:ring-2 focus:ring-gold/20",
        "placeholder:text-ink-muted",
        // Ensure text remains readable in all states
        "[color-scheme:dark]",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
      style={{
        WebkitTextFillColor: '#e2e8f0',
        WebkitBoxShadow: '0 0 0px 1000px #1c2133 inset',
        transition: 'background-color 5000s ease-in-out 0s'
      }}
      {...props}
    />
  );
}
