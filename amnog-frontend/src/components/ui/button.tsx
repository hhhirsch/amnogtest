import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-r from-primary-600 to-primary-700 text-white shadow-md hover:shadow-lg hover:from-primary-700 hover:to-primary-800 active:scale-[0.98]",
        outline: "border-2 border-slate-300 bg-white hover:bg-slate-50 hover:border-slate-400 active:scale-[0.98]",
        ghost: "hover:bg-slate-100 active:bg-slate-200",
        success: "bg-gradient-to-r from-success-600 to-success-700 text-white shadow-md hover:shadow-lg hover:from-success-700 hover:to-success-800 active:scale-[0.98]",
      },
      size: {
        default: "h-11 px-5 py-2.5",
        sm: "h-9 px-4 text-xs",
        lg: "h-12 px-6 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type, ...props }, ref) => (
    <button
      ref={ref}
      type={type ?? "button"}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
);

Button.displayName = "Button";