import { cn } from "@/lib/utils";

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn("h-11 w-full rounded-lg border-2 border-slate-200 bg-white px-4 text-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100 cursor-pointer")} {...props} />;
}
