import { cn } from "@/lib/utils";

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "bg-bg2 border border-white/[0.13] rounded-[10px] px-4 py-3 text-sm text-ink font-sans outline-none w-full transition-all duration-200",
        "focus:border-gold focus:bg-[#1c2133] focus:ring-2 focus:ring-gold/20",
        "appearance-none bg-no-repeat",
        "bg-[position:right_14px_center]"
      )}
      style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L6 6L11 1' stroke='%23e2e8f0' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`
      }}
      {...props}
    />
  );
}
