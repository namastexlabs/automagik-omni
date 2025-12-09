import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

interface RestartRequiredBannerProps {
  runtimeDbType: string;
  savedDbType: string;
  reason?: string | null;
}

/**
 * Amber warning banner shown when runtime config differs from saved config.
 * Indicates that a restart is required to apply changes.
 */
export function RestartRequiredBanner({ runtimeDbType, savedDbType, reason }: RestartRequiredBannerProps) {
  return (
    <Alert className="border-amber-400 bg-amber-50 dark:bg-amber-950">
      <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
      <AlertTitle className="text-amber-800 dark:text-amber-200 flex items-center gap-2">
        <RefreshCw className="h-4 w-4" />
        Restart Required
      </AlertTitle>
      <AlertDescription className="text-amber-700 dark:text-amber-300">
        <p className="mb-2">
          Your saved configuration differs from the running configuration. Restart the application to apply changes.
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
            Running: {runtimeDbType}
          </Badge>
          <span className="text-amber-600">→</span>
          <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
            Saved: {savedDbType}
          </Badge>
        </div>
        {reason && <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">Reason: {reason}</p>}
      </AlertDescription>
    </Alert>
  );
}
