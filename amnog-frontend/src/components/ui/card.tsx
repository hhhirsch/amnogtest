import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  goldBorder?: boolean;
}

export function Card({ className, goldBorder, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-700 bg-slate-800 p-4 shadow-sm",
        goldBorder && "border-l-4 border-l-gold-500",
        className
      )}
      {...props}
    />
  );
}
