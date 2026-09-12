import type { HTMLAttributes } from 'react';

type Props = HTMLAttributes<HTMLDivElement>;

export function Card({ className = '', ...props }: Props) {
  return (
    <div
      className={`bg-surface border border-border rounded-lg p-6 ${className}`}
      {...props}
    />
  );
}
