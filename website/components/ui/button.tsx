import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#20808d] disabled:pointer-events-none disabled:opacity-50 select-none",
  {
    variants: {
      variant: {
        default:
          "bg-[#20808d] text-white shadow-sm hover:bg-[#016a71] active:bg-[#015258]",
        destructive:
          "bg-[#c25450] text-white shadow-sm hover:bg-[#b24743] active:bg-[#9e3e3a]",
        outline:
          "border border-[#e7e5e0] bg-[#fdfbfa] text-[#1f1915] shadow-sm hover:bg-[#f5f4ef] hover:text-[#1f1915]",
        secondary:
          "bg-[#f5f4ef] text-[#1f1915] shadow-sm hover:bg-[#ebe9e2] hover:text-[#1f1915]",
        ghost:
          "text-[#6b675f] hover:bg-[#f5f4ef] hover:text-[#1f1915]",
        link: "text-[#20808d] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-8 w-8 rounded-md p-0",
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

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
