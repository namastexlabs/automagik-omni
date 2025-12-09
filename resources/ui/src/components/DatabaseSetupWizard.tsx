import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Database, CheckCircle2, AlertTriangle, HardDrive, ChevronDown, ChevronRight, FolderOpen } from 'lucide-react';
import { DatabaseConfig } from '@/types/onboarding';

interface DatabaseSetupWizardProps {
  onComplete?: (config: DatabaseConfig) => void;
  isFirstRun?: boolean;
}

export function DatabaseSetupWizard({ onComplete, isFirstRun = false }: DatabaseSetupWizardProps) {
  // Storage mode: 'filesystem' or 'memory' (embedded pgserve only)
  const [storageMode, setStorageMode] = useState<'filesystem' | 'memory'>('filesystem');

  // Filesystem mode options
  const [dataDir, setDataDir] = useState('./data/postgres');

  // Redis configuration (optional)
  const [redisEnabled, setRedisEnabled] = useState(false);
  const [redisUrl, setRedisUrl] = useState('');
  const [showAdvancedRedis, setShowAdvancedRedis] = useState(false);
  const [redisPrefixKey, setRedisPrefixKey] = useState('omni');
  const [redisTtl, setRedisTtl] = useState(604800);
  const [redisSaveInstances, setRedisSaveInstances] = useState(true);

  const handleComplete = () => {
    const config: DatabaseConfig = {
      // PostgreSQL storage options (embedded pgserve)
      data_dir: storageMode === 'filesystem' ? dataDir : undefined,
      memory_mode: storageMode === 'memory',
      replication_enabled: false,

      // Redis cache (optional)
      redis_enabled: redisEnabled,
      redis_url: redisEnabled ? redisUrl : undefined,
      redis_prefix_key: redisEnabled ? redisPrefixKey : undefined,
      redis_ttl: redisEnabled ? redisTtl : undefined,
      redis_save_instances: redisEnabled ? redisSaveInstances : undefined,
    };

    onComplete?.(config);
  };

  const isValid = storageMode === 'filesystem' ? dataDir.trim().length > 0 : true; // memory mode always valid

  return (
    <Card className="border-border elevation-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          PostgreSQL Storage Configuration
        </CardTitle>
        <CardDescription>Configure embedded PostgreSQL storage. Data is stored locally using pgserve.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* PostgreSQL Storage Mode */}
        <div className="space-y-4">
          <div>
            <Label className="text-base font-semibold">Storage Mode</Label>
            <p className="text-sm text-muted-foreground mt-1">Choose how PostgreSQL stores data.</p>
          </div>

          {/* Option 1: Filesystem (Production) */}
          <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-accent transition-colors">
            <input
              type="radio"
              value="filesystem"
              checked={storageMode === 'filesystem'}
              onChange={() => setStorageMode('filesystem')}
              className="mt-1"
            />
            <div className="flex-1">
              <div className="font-medium">Filesystem Storage (Recommended for Production)</div>
              <p className="text-sm text-muted-foreground">Persistent data stored on disk</p>
            </div>
          </label>

          {storageMode === 'filesystem' && (
            <div className="space-y-2 pl-7">
              <Label htmlFor="data-dir" className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4" />
                Data Directory
              </Label>
              <Input
                id="data-dir"
                type="text"
                placeholder="./data/postgres"
                value={dataDir}
                onChange={(e) => setDataDir(e.target.value)}
                className="font-mono"
              />
              <p className="text-xs text-muted-foreground">
                Path where PostgreSQL data files will be stored. Defaults to ./data/postgres
              </p>
            </div>
          )}

          {/* Option 2: Memory Only */}
          <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-accent transition-colors">
            <input
              type="radio"
              value="memory"
              checked={storageMode === 'memory'}
              onChange={() => setStorageMode('memory')}
              className="mt-1"
            />
            <div className="flex-1">
              <div className="font-medium">Memory Storage (Development)</div>
              <p className="text-sm text-muted-foreground">Embedded PostgreSQL in RAM, data lost on restart</p>
            </div>
          </label>

          {storageMode === 'memory' && (
            <Alert className="ml-7">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>Data will be lost on restart (memory only, no persistence)</AlertDescription>
            </Alert>
          )}
        </div>

        {/* Redis Cache Configuration (Optional) */}
        <div className="border-t pt-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <HardDrive className="h-5 w-5 text-muted-foreground" />
              <div>
                <Label className="text-base font-semibold">Redis Cache (Optional)</Label>
                <p className="text-xs text-muted-foreground">Enable Redis caching for faster instance restarts</p>
              </div>
            </div>
            <Switch checked={redisEnabled} onCheckedChange={setRedisEnabled} />
          </div>

          {redisEnabled && (
            <div className="space-y-4 pl-7">
              <div className="space-y-2">
                <Label htmlFor="redis-url">Redis URL</Label>
                <Input
                  id="redis-url"
                  type="text"
                  placeholder="redis://localhost:6379/0"
                  value={redisUrl}
                  onChange={(e) => setRedisUrl(e.target.value)}
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">Redis connection URL (redis:// or rediss:// for TLS)</p>
              </div>

              <Collapsible open={showAdvancedRedis} onOpenChange={setShowAdvancedRedis}>
                <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                  {showAdvancedRedis ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  Advanced Redis options
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="redis-prefix">Key Prefix</Label>
                    <Input
                      id="redis-prefix"
                      type="text"
                      placeholder="omni"
                      value={redisPrefixKey}
                      onChange={(e) => setRedisPrefixKey(e.target.value)}
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground">Prefix for all Redis keys (default: omni)</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="redis-ttl">TTL (seconds)</Label>
                    <Input
                      id="redis-ttl"
                      type="number"
                      placeholder="604800"
                      value={redisTtl}
                      onChange={(e) => setRedisTtl(parseInt(e.target.value) || 604800)}
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground">
                      Time-to-live for cached data (default: 604800 = 7 days)
                    </p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="redis-save-instances">Save Instances in Redis</Label>
                      <p className="text-xs text-muted-foreground">Store instance state in Redis for faster restarts</p>
                    </div>
                    <Switch
                      id="redis-save-instances"
                      checked={redisSaveInstances}
                      onCheckedChange={setRedisSaveInstances}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          )}
        </div>

        {/* Summary Alert */}
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Configuration Summary</AlertTitle>
          <AlertDescription className="space-y-2">
            <ul className="list-disc list-inside text-sm">
              <li>
                PostgreSQL:{' '}
                <strong>
                  {storageMode === 'filesystem' && `Embedded (Filesystem: ${dataDir})`}
                  {storageMode === 'memory' && 'Embedded (Memory Only)'}
                </strong>
              </li>
              <li>
                Redis Cache: <strong>{redisEnabled ? 'Enabled' : 'Disabled'}</strong>
              </li>
            </ul>
          </AlertDescription>
        </Alert>

        {/* Complete Button */}
        <div className="flex justify-end pt-4">
          <Button onClick={handleComplete} disabled={!isValid} size="lg" className="w-full sm:w-auto">
            <CheckCircle2 className="h-4 w-4 mr-2" />
            Continue to API Key Setup
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
