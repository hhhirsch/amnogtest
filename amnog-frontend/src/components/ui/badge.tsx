import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px]",
  {
    variants: {
      variant: {
        default: "bg-surface2 border-white/[0.13] text-ink-soft",
        gold: "border-gold-500 bg-gold-500/10 text-gold-400",
        warning: "bg-gold/10 border-gold/30 text-gold",
        red: "border-red-500 bg-red-500/10 text-red-400",
        green: "border-green-500 bg-green-500/10 text-green-400",
        yellow: "border-yellow-500 bg-yellow-500/10 text-yellow-400",
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
      {variant === "warning" ? (
        <span className="h-[5px] w-[5px] rounded-full bg-gold" />
      ) : (
        dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />
      )}
      {children}
    </div>
  );
}
