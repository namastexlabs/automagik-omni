import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { api, getApiKey, formatDateTime } from '@/lib';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Settings as SettingsIcon, Key, Info, Moon, Sun, Database, ArrowRight } from 'lucide-react';

export default function Settings() {
  const navigate = useNavigate();
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
  });

  const apiKey = getApiKey();
  const maskedKey = apiKey ? `${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 4)}` : 'Not set';

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Settings"
          subtitle="Configure your Omni UI preferences"
          icon={<SettingsIcon className="h-6 w-6 text-primary" />}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in max-w-4xl">
            {/* API Configuration */}
            <Card className="border-border elevation-md">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Key className="h-5 w-5 text-primary" />
                  <CardTitle>API Configuration</CardTitle>
                </div>
                <CardDescription>Your Omni API connection settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <span className="text-sm font-medium text-foreground">API URL</span>
                  <code className="text-sm text-muted-foreground">
                    {import.meta.env.VITE_API_URL || 'http://localhost:8882'}
                  </code>
                </div>

                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <span className="text-sm font-medium text-foreground">API Key</span>
                  <code className="text-sm text-muted-foreground font-mono">{maskedKey}</code>
                </div>

                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <span className="text-sm font-medium text-foreground">API Status</span>
                  {health ? (
                    <Badge className={health.status === 'up' ? 'gradient-success border-0' : 'bg-destructive border-0'}>
                      {health.status === 'up' ? 'Connected' : health.status}
                    </Badge>
                  ) : (
                    <Badge variant="outline">Checking...</Badge>
                  )}
                </div>

                {health?.version && (
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                    <span className="text-sm font-medium text-foreground">API Version</span>
                    <code className="text-sm text-muted-foreground">{health.version}</code>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Global Settings Link */}
            <Card className="border-border elevation-md hover:elevation-lg transition-all cursor-pointer" onClick={() => navigate('/global-settings')}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="h-5 w-5 text-primary" />
                    <CardTitle>Global Settings</CardTitle>
                  </div>
                  <ArrowRight className="h-5 w-5 text-muted-foreground" />
                </div>
                <CardDescription>Manage system-wide configuration and WhatsApp Web settings</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Configure WhatsApp Web credentials, system limits, and other global settings that apply across all instances.
                </p>
                <Button className="mt-4" onClick={(e) => { e.stopPropagation(); navigate('/global-settings'); }}>
                  Open Global Settings
                </Button>
              </CardContent>
            </Card>

            {/* Theme Settings */}
            <Card className="border-border elevation-md">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Moon className="h-5 w-5 text-primary dark:hidden" />
                  <Sun className="h-5 w-5 text-primary hidden dark:block" />
                  <CardTitle>Appearance</CardTitle>
                </div>
                <CardDescription>Customize the look and feel of the interface</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <div>
                    <span className="text-sm font-medium text-foreground block">Theme</span>
                    <span className="text-xs text-muted-foreground">
                      Toggle between light and dark mode
                    </span>
                  </div>
                  <ThemeToggle />
                </div>

                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <span className="text-sm font-medium text-foreground">Primary Color</span>
                  <div className="flex items-center gap-2">
                    <div className="h-6 w-6 rounded-full gradient-primary border-2 border-border"></div>
                    <code className="text-sm text-muted-foreground">Purple</code>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* About */}
            <Card className="border-border elevation-md">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Info className="h-5 w-5 text-primary" />
                  <CardTitle>About</CardTitle>
                </div>
                <CardDescription>Information about Automagik Omni UI</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <span className="text-sm font-medium text-foreground">Application</span>
                  <span className="text-sm text-muted-foreground">Automagik Omni UI</span>
                </div>

                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <span className="text-sm font-medium text-foreground">Version</span>
                  <code className="text-sm text-muted-foreground">0.1.0</code>
                </div>

                <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                  <span className="text-sm font-medium text-foreground">Framework</span>
                  <span className="text-sm text-muted-foreground">React 19 + Vite 6</span>
                </div>

                {health?.timestamp && (
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                    <span className="text-sm font-medium text-foreground">Last API Check</span>
                    <span className="text-sm text-muted-foreground">
                      {formatDateTime(health.timestamp)}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Footer */}
            <div className="pt-6 pb-4">
              <Separator className="mb-4" />
              <p className="text-xs text-center text-muted-foreground">
                Automagik Omni - Unified Multi-Channel Messaging Hub
                <br />
                Built with React, TypeScript, and shadcn/ui
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
