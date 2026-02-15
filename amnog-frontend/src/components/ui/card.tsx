import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition-shadow hover:shadow-lg", className)} {...props} />;
}
