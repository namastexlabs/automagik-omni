import type { ReactNode } from 'react';
import { ThemeToggle } from './ThemeToggle';
import { McpConfigCopy } from './McpConfigCopy';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  actions?: ReactNode;
  showMcpButton?: boolean;
  showThemeToggle?: boolean;
}

export function PageHeader({
  title,
  subtitle,
  icon,
  actions,
  showMcpButton = true,
  showThemeToggle = true,
}: PageHeaderProps) {
  return (
    <div className="border-b border-border bg-card">
      <div className="flex h-20 items-center px-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            {icon}
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-1">
              {subtitle}
            </p>
          )}
        </div>
        <div className="ml-auto flex items-center space-x-3">
          {actions}
          {showMcpButton && <McpConfigCopy />}
          {showThemeToggle && <ThemeToggle />}
        </div>
      </div>
    </div>
  );
}
