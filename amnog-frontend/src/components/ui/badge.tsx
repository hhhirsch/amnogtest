import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-medium whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "border-slate-600 bg-slate-800 text-slate-300",
        gold: "border-gold-500 bg-gold-500/10 text-gold-400",
        red: "border-red-500 bg-red-500/10 text-red-400",
        green: "border-green-500 bg-green-500/10 text-green-400",
        yellow: "border-yellow-500 bg-yellow-500/10 text-yellow-400",
        low: "bg-red-500/10 border-red-500/25 text-red-400",
        medium: "bg-amber-500/10 border-amber-500/25 text-amber-400",
        high: "bg-green-500/10 border-green-500/25 text-green-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({ className, variant, dot, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, className }))} {...props}>
      {dot && <span className="h-[5px] w-[5px] rounded-full bg-current" />}
      {children}
    </div>
  );
}
