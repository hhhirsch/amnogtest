import { cn } from "@/lib/utils";

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-md border border-slate-600 bg-slate-800 px-3 text-sm text-slate-100 focus:border-gold-500 focus:outline-none focus:ring-1 focus:ring-gold-500"
      )}
      {...props}
    />
  );
}
