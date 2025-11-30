import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib';
import { Database, Settings, AlertCircle } from 'lucide-react';
import { RestartRequiredBanner } from './RestartRequiredBanner';
import { DatabaseStatusCard } from './DatabaseStatusCard';
import { LockedDatabaseTypeBadge } from './LockedDatabaseTypeBadge';
import { DatabaseSetupWizard } from '@/components/DatabaseSetupWizard';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useState } from 'react';

/**
 * Main orchestrator component for database configuration display on GlobalSettings page.
 * Shows runtime vs saved config, restart warnings, and locked state indicators.
 */
export function DatabaseConfigSection() {
  const [wizardOpen, setWizardOpen] = useState(false);

  // Fetch database configuration state
  const { data: config, isLoading, error, refetch } = useQuery({
    queryKey: ['database-config'],
    queryFn: () => api.database.getConfig(),
  });

  if (isLoading) {
    return (
      <Card className="border-border">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            <CardTitle>Database Configuration</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <CardTitle>Database Configuration</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">
            Failed to load database configuration. Please refresh the page.
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-2">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!config) {
    return null;
  }

  const isSynced = !config.requires_restart;

  return (
    <Card className="border-border elevation-md">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            <CardTitle>Database Configuration</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <LockedDatabaseTypeBadge
              dbType={config.saved?.db_type || config.runtime.db_type}
              isLocked={config.is_locked}
            />
            {config.is_configured && !config.is_locked && (
              <Dialog open={wizardOpen} onOpenChange={setWizardOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Settings className="h-4 w-4 mr-1" />
                    Configure
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
                  <DialogHeader>
                    <DialogTitle>Database Configuration</DialogTitle>
                    <DialogDescription>
                      Update your database settings. Changes will require a restart to take effect.
                    </DialogDescription>
                  </DialogHeader>
                  <DatabaseSetupWizard
                    onComplete={() => {
                      setWizardOpen(false);
                      refetch();
                    }}
                  />
                </DialogContent>
              </Dialog>
            )}
          </div>
        </div>
        <CardDescription>
          {config.is_configured
            ? 'Current database configuration state'
            : 'Database has not been configured via the setup wizard'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Restart Required Banner */}
        {config.requires_restart && config.saved && (
          <RestartRequiredBanner
            runtimeDbType={config.runtime.db_type}
            savedDbType={config.saved.db_type || 'unknown'}
            reason={config.restart_required_reason}
          />
        )}

        {/* Status Cards */}
        <DatabaseStatusCard
          runtime={config.runtime}
          saved={config.saved}
          isSynced={isSynced}
        />

        {/* First-time Setup - Show wizard inline when not configured */}
        {!config.is_configured && (
          <div className="mt-4">
            <DatabaseSetupWizard
              onComplete={() => refetch()}
            />
          </div>
        )}

        {/* Locked Notice for users trying to change */}
        {config.is_locked && (
          <p className="text-xs text-muted-foreground text-center pt-2">
            Database type is locked because messaging instances exist.
            To change database type, all instances must be removed first.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
