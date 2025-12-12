import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib';
import { LayoutDashboard, MessageSquare, Users, Settings, LogOut, Shield, Server, Plug } from 'lucide-react';
import { InstanceNav } from './sidebar/InstanceNav';

interface SidebarProps {
  onLogout: () => void;
  onNavigate?: () => void;
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Chats', href: '/chats', icon: MessageSquare },
  { name: 'Contacts', href: '/contacts', icon: Users },
  { name: 'Access Rules', href: '/access-rules', icon: Shield },
  { name: 'Services', href: '/services', icon: Server },
  { name: 'MCP', href: '/mcp', icon: Plug },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar({ onLogout, onNavigate }: SidebarProps) {
  const location = useLocation();
  const [instancesExpanded, setInstancesExpanded] = useState(true);

  const handleNavClick = () => {
    onNavigate?.();
  };

  return (
    <div className="flex h-full w-64 flex-col bg-card border-r border-border elevation-sm">
      {/* Logo - Match dashboard header height exactly */}
      <div className="flex items-center justify-center border-b border-border px-6 py-3">
        <img src="/omni-logo.svg" alt="Omni" className="h-14 w-auto" />
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto space-y-1 px-3 py-6">
        {/* Dashboard Link */}
        <Link
          to="/dashboard"
          onClick={handleNavClick}
          className={cn(
            'group flex items-center space-x-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200',
            location.pathname === '/dashboard'
              ? 'bg-primary text-primary-foreground elevation-md'
              : 'text-foreground hover:bg-accent hover:text-accent-foreground',
          )}
        >
          <LayoutDashboard
            className={cn(
              'h-5 w-5 transition-transform group-hover:scale-110',
              location.pathname === '/dashboard'
                ? 'text-primary-foreground'
                : 'text-muted-foreground group-hover:text-accent-foreground',
            )}
          />
          <span>Dashboard</span>
          {location.pathname === '/dashboard' && (
            <div className="ml-auto h-2 w-2 rounded-full bg-primary-foreground/80 animate-pulse"></div>
          )}
        </Link>

        {/* Instances Nav with Expandable Sub-items */}
        <InstanceNav
          isExpanded={instancesExpanded}
          onToggle={() => setInstancesExpanded(!instancesExpanded)}
          onNavigate={onNavigate}
        />

        {/* Other Navigation Items */}
        {navigation
          .filter((item) => item.name !== 'Dashboard')
          .map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={handleNavClick}
                className={cn(
                  'group flex items-center space-x-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-primary text-primary-foreground elevation-md'
                    : 'text-foreground hover:bg-accent hover:text-accent-foreground',
                )}
              >
                <item.icon
                  className={cn(
                    'h-5 w-5 transition-transform group-hover:scale-110',
                    isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground',
                  )}
                />
                <span>{item.name}</span>
                {isActive && (
                  <div className="ml-auto h-2 w-2 rounded-full bg-primary-foreground/80 animate-pulse"></div>
                )}
              </Link>
            );
          })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-4">
        <button
          onClick={onLogout}
          className="flex w-full items-center space-x-3 rounded-lg px-4 py-3 text-sm font-medium text-destructive hover:bg-destructive/10 transition-all group focus-ring"
        >
          <LogOut className="h-5 w-5 group-hover:scale-110 transition-transform" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
}
