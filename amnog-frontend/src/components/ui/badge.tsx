import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("inline-flex rounded-full border px-2 py-1 text-xs font-medium", className)} {...props} />;
}
