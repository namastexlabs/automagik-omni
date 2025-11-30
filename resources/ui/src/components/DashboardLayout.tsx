import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, PanelLeftClose, PanelLeft } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { StatusFooter } from './StatusFooter';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { cn, removeApiKey } from '@/lib';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);

  const handleLogout = () => {
    removeApiKey();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile sidebar - Sheet/Drawer */}
      <div className="lg:hidden">
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="fixed top-3 left-3 z-50 h-10 w-10 bg-card border border-border shadow-md"
            >
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-64">
            <Sidebar onLogout={handleLogout} onNavigate={() => setMobileOpen(false)} />
          </SheetContent>
        </Sheet>
      </div>

      {/* Desktop sidebar - collapsible */}
      <div
        className={cn(
          "hidden lg:flex flex-col transition-all duration-300 ease-in-out relative",
          desktopCollapsed ? "w-0" : "w-64"
        )}
      >
        {!desktopCollapsed && (
          <Sidebar onLogout={handleLogout} />
        )}

        {/* Desktop collapse/expand button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setDesktopCollapsed(!desktopCollapsed)}
          className={cn(
            "absolute top-3 z-50 h-8 w-8 bg-card border border-border shadow-sm hover:bg-accent",
            desktopCollapsed ? "left-3" : "-right-4"
          )}
        >
          {desktopCollapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          {children}
        </div>
        <StatusFooter />
      </div>
    </div>
  );
}
