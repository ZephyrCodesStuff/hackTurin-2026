import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[#20808d] text-white shadow-sm hover:bg-[#016a71]",
        secondary:
          "border-transparent bg-[#f5f4ef] text-[#1f1915] hover:bg-[#ebe9e2]",
        destructive:
          "border-transparent bg-[#c25450] text-white shadow-sm hover:bg-[#b24743]",
        outline: "text-[#1f1915] border-[#e7e5e0]",
        success:
          "border-[#4f9d69]/30 bg-[#4f9d69]/10 text-[#3f7d54]",
        warning:
          "border-[#c08a2d]/30 bg-[#c08a2d]/10 text-[#9a6e22]",
        danger:
          "border-[#c25450]/30 bg-[#c25450]/10 text-[#a8423e]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
