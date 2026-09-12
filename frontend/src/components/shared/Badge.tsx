import type { HTMLAttributes } from 'react';

type Status = 'active' | 'danger' | 'warning' | 'success';

type Props = HTMLAttributes<HTMLSpanElement> & {
  status: Status;
};

const statusClasses: Record<Status, string> = {
  active: 'bg-accent-muted text-accent-light',
  danger: 'bg-danger-muted text-danger-light',
  warning: 'bg-warning-muted text-warning-light',
  success: 'bg-success-muted text-success-light',
};

export function Badge({ status, className = '', ...props }: Props) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusClasses[status]} ${className}`}
      {...props}
    />
  );
}
