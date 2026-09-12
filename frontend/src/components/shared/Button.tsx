import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const base =
  'inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none';

const variants: Record<Variant, string> = {
  primary: 'bg-accent text-accent-foreground hover:bg-accent-dark',
  secondary:
    'border border-border bg-transparent text-text-secondary hover:border-border-light hover:text-text-primary',
};

export function Button({ variant = 'primary', className = '', ...props }: Props) {
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}
