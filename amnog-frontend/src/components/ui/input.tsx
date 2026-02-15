import { cn } from "@/lib/utils";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn("h-11 w-full rounded-lg border-2 border-slate-200 bg-white px-4 text-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100 placeholder:text-slate-400")} {...props} />;
}
