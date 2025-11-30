import { Zap, Database, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { RuntimeDatabaseConfig, SavedDatabaseConfig } from '@/lib';

interface DatabaseStatusCardProps {
  runtime: RuntimeDatabaseConfig;
  saved: SavedDatabaseConfig | null;
  isSynced: boolean;
}

/**
 * Dual-panel display showing Running vs Saved database configuration.
 * Green panel for runtime, blue panel for saved config.
 */
export function DatabaseStatusCard({
  runtime,
  saved,
  isSynced,
}: DatabaseStatusCardProps) {
  const formatDbType = (type: string | null) => {
    if (!type) return 'Not configured';
    return type === 'postgresql' ? 'PostgreSQL' :
           type === 'sqlite' ? 'SQLite' : type;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;
      return date.toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center justify-between">
          Current Status
          {isSynced && (
            <Badge variant="outline" className="text-green-600 border-green-300 bg-green-50 dark:bg-green-950">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              In Sync
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Running Configuration Panel */}
          <div className="p-4 rounded-lg border border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="h-4 w-4 text-green-600 dark:text-green-400" />
              <span className="font-medium text-green-800 dark:text-green-200">Running</span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-green-700 dark:text-green-300">Type:</span>
                <span className="font-medium text-green-900 dark:text-green-100">
                  {formatDbType(runtime.db_type)}
                </span>
              </div>
              {runtime.use_postgres && runtime.postgres_url_masked && (
                <div className="flex justify-between">
                  <span className="text-green-700 dark:text-green-300">Connection:</span>
                  <span className="font-mono text-xs text-green-900 dark:text-green-100 truncate max-w-[180px]">
                    {runtime.postgres_url_masked}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-green-700 dark:text-green-300">Pool Size:</span>
                <span className="font-medium text-green-900 dark:text-green-100">
                  {runtime.pool_size}
                </span>
              </div>
            </div>
          </div>

          {/* Saved Configuration Panel */}
          <div className="p-4 rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
            <div className="flex items-center gap-2 mb-3">
              <Database className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span className="font-medium text-blue-800 dark:text-blue-200">Saved</span>
            </div>
            {saved ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-blue-700 dark:text-blue-300">Type:</span>
                  <span className="font-medium text-blue-900 dark:text-blue-100">
                    {formatDbType(saved.db_type)}
                  </span>
                </div>
                {saved.postgres_host && (
                  <div className="flex justify-between">
                    <span className="text-blue-700 dark:text-blue-300">Host:</span>
                    <span className="font-medium text-blue-900 dark:text-blue-100">
                      {saved.postgres_host}:{saved.postgres_port || '5432'}
                    </span>
                  </div>
                )}
                {saved.redis_enabled && (
                  <div className="flex justify-between">
                    <span className="text-blue-700 dark:text-blue-300">Redis:</span>
                    <Badge variant="outline" className="text-xs border-blue-300 text-blue-700 dark:text-blue-300">
                      Enabled
                    </Badge>
                  </div>
                )}
                {saved.last_updated_at && (
                  <div className="flex justify-between">
                    <span className="text-blue-700 dark:text-blue-300">Updated:</span>
                    <span className="text-blue-900 dark:text-blue-100">
                      {formatDate(saved.last_updated_at)}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-blue-600 dark:text-blue-400 italic">
                Not configured via wizard
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
