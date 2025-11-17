import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Settings,
  Activity,
  LogOut,
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  onLogout: () => void;
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Instances', href: '/instances', icon: Activity },
  { name: 'Chats', href: '/chats', icon: MessageSquare },
  { name: 'Contacts', href: '/contacts', icon: Users },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar({ onLogout }: SidebarProps) {
  const location = useLocation();

  return (
    <div className="flex h-full w-64 flex-col bg-card border-r border-border elevation-sm">
      {/* Logo */}
      <div className="flex h-20 items-center border-b border-border px-6">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className="h-10 w-10 rounded-lg gradient-primary flex items-center justify-center elevation-md">
              <Sparkles className="h-6 w-6 text-primary-foreground" />
            </div>
            <div className="absolute -top-1 -right-1 h-3 w-3 bg-success rounded-full border-2 border-card">
              <div className="h-full w-full bg-success/80 rounded-full animate-pulse"></div>
            </div>
          </div>
          <div>
            <span className="text-xl font-bold text-foreground">
              Omni
            </span>
            <p className="text-xs text-muted-foreground">Messaging Hub</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-6">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'group flex items-center space-x-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-primary text-primary-foreground elevation-md'
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className={cn(
                'h-5 w-5 transition-transform group-hover:scale-110',
                isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground'
              )} />
              <span>{item.name}</span>
              {isActive && (
                <div className="ml-auto h-2 w-2 rounded-full bg-primary-foreground/80 animate-pulse"></div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Stats/Info Section */}
      <div className="px-3 py-4 space-y-3">
        <div className="rounded-lg bg-success/10 p-4 border border-success/20">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-success">API Status</span>
            <div className="h-2 w-2 bg-success rounded-full animate-pulse"></div>
          </div>
          <p className="text-sm font-semibold text-success">Connected</p>
          <p className="text-xs text-success/80 mt-1">All systems operational</p>
        </div>
      </div>

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
