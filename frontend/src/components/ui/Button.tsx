interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'success' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
}

const variants: Record<string, string> = {
  primary: 'bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white',
  success: 'bg-[var(--success)] hover:opacity-90 text-white',
  danger: 'bg-[var(--danger)] hover:opacity-90 text-white',
  ghost: 'bg-transparent hover:bg-[var(--surface-hover)] text-[var(--text)]',
}

const sizes: Record<string, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
}

export function Button({ variant = 'primary', size = 'md', className = '', disabled, children, ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-lg font-medium transition-colors ${variants[variant]} ${sizes[size]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}
