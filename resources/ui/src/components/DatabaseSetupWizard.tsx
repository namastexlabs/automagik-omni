import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { api, DatabaseTestResponse, RedisTestResponse, TestResult } from '@/lib';
import {
  Database,
  Server,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Zap,
  HardDrive,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

type WizardStep = 'select' | 'configure' | 'confirm';

interface DatabaseSetupWizardProps {
  onComplete?: () => void;
}

export function DatabaseSetupWizard({ onComplete }: DatabaseSetupWizardProps) {
  const [step, setStep] = useState<WizardStep>('select');
  const [dbType, setDbType] = useState<'sqlite' | 'postgresql'>('sqlite');
  const [postgresUrl, setPostgresUrl] = useState('');
  const [testResult, setTestResult] = useState<DatabaseTestResponse | null>(null);

  // Redis configuration state
  const [redisEnabled, setRedisEnabled] = useState(false);
  const [redisUrl, setRedisUrl] = useState('');
  const [redisPrefixKey, setRedisPrefixKey] = useState('evolution');
  const [redisTtl, setRedisTtl] = useState(604800);
  const [redisSaveInstances, setRedisSaveInstances] = useState(true);
  const [redisTestResult, setRedisTestResult] = useState<RedisTestResponse | null>(null);
  const [showAdvancedRedis, setShowAdvancedRedis] = useState(false);

  // Fetch current config
  const { data: currentConfig, isLoading: configLoading } = useQuery({
    queryKey: ['database-config'],
    queryFn: () => api.database.getConfig(),
  });

  // Detect Evolution database
  const detectMutation = useMutation({
    mutationFn: () => api.database.detectEvolution(),
    onSuccess: (data) => {
      if (data.found && data.url_masked) {
        // Note: we only get masked URL, user needs to enter full URL
        // But we can show them it was detected
      }
    },
  });

  // Test connection
  const testMutation = useMutation({
    mutationFn: (url: string) => api.database.testConnection(url),
    onSuccess: (data) => {
      setTestResult(data);
    },
  });

  // Test Redis connection
  const redisTestMutation = useMutation({
    mutationFn: (url: string) => api.database.testRedisConnection(url),
    onSuccess: (data) => {
      setRedisTestResult(data);
    },
  });

  // Apply configuration
  const applyMutation = useMutation({
    mutationFn: () =>
      api.database.apply(
        dbType,
        dbType === 'postgresql' ? postgresUrl : undefined,
        {
          enabled: redisEnabled,
          url: redisEnabled ? redisUrl : undefined,
          prefixKey: redisPrefixKey,
          ttl: redisTtl,
          saveInstances: redisSaveInstances,
        }
      ),
    onSuccess: () => {
      onComplete?.();
    },
  });

  const handleTestConnection = () => {
    if (postgresUrl) {
      testMutation.mutate(postgresUrl);
    }
  };

  const handleTestRedisConnection = () => {
    if (redisUrl) {
      redisTestMutation.mutate(redisUrl);
    }
  };

  const handleDetectEvolution = () => {
    detectMutation.mutate();
  };

  const canProceedToConfigure = dbType === 'sqlite' || (dbType === 'postgresql');
  const canProceedToConfirm =
    (dbType === 'sqlite' || testResult?.success === true) &&
    (!redisEnabled || redisTestResult?.success === true);

  const renderTestResult = (name: string, result: TestResult) => {
    const Icon = result.ok ? CheckCircle2 : XCircle;
    const colorClass = result.ok ? 'text-green-500' : 'text-red-500';

    return (
      <div key={name} className="flex items-center gap-2 text-sm">
        <Icon className={`h-4 w-4 ${colorClass}`} />
        <span className="capitalize font-medium">{name.replace('_', ' ')}</span>
        <span className="text-muted-foreground">{result.message}</span>
        {result.latency_ms && (
          <Badge variant="outline" className="text-xs">
            {result.latency_ms.toFixed(0)}ms
          </Badge>
        )}
      </div>
    );
  };

  if (configLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <Card className="border-border elevation-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Database Configuration
        </CardTitle>
        <CardDescription>
          Configure your database backend. Choose between local SQLite or shared PostgreSQL.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Current Status */}
        {currentConfig && (
          <Alert>
            <Database className="h-4 w-4" />
            <AlertTitle>Current Configuration</AlertTitle>
            <AlertDescription>
              Using <strong>{currentConfig.db_type}</strong>
              {currentConfig.use_postgres && (
                <span> with table prefix <code>{currentConfig.table_prefix}</code></span>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Step 1: Select Database Type */}
        {step === 'select' && (
          <div className="space-y-4">
            <Label className="text-base font-semibold">Choose Database Type</Label>
            <RadioGroup
              value={dbType}
              onValueChange={(v) => setDbType(v as 'sqlite' | 'postgresql')}
              className="grid grid-cols-1 md:grid-cols-2 gap-4"
            >
              <Label
                htmlFor="sqlite"
                className={`flex flex-col items-start gap-2 rounded-lg border p-4 cursor-pointer transition-colors ${
                  dbType === 'sqlite' ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted'
                }`}
              >
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="sqlite" id="sqlite" />
                  <span className="font-semibold">SQLite (Local)</span>
                </div>
                <p className="text-sm text-muted-foreground pl-6">
                  Simple, self-contained database stored locally. Best for single-node deployments.
                </p>
              </Label>

              <Label
                htmlFor="postgresql"
                className={`flex flex-col items-start gap-2 rounded-lg border p-4 cursor-pointer transition-colors ${
                  dbType === 'postgresql' ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted'
                }`}
              >
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="postgresql" id="postgresql" />
                  <span className="font-semibold">PostgreSQL (Shared)</span>
                </div>
                <p className="text-sm text-muted-foreground pl-6">
                  Share database with Evolution API. Uses <code>omni_</code> table prefix for isolation.
                </p>
              </Label>
            </RadioGroup>

            <div className="flex justify-end pt-4">
              <Button onClick={() => setStep('configure')} disabled={!canProceedToConfigure}>
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Configure */}
        {step === 'configure' && (
          <div className="space-y-4">
            {dbType === 'sqlite' ? (
              <Alert>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <AlertTitle>SQLite Selected</AlertTitle>
                <AlertDescription>
                  SQLite requires no additional configuration. Data will be stored locally in the data directory.
                </AlertDescription>
              </Alert>
            ) : (
              <>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="postgres-url">PostgreSQL Connection URL</Label>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleDetectEvolution}
                      disabled={detectMutation.isPending}
                    >
                      {detectMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Zap className="h-4 w-4 mr-1" />
                      )}
                      Detect Evolution
                    </Button>
                  </div>
                  <Input
                    id="postgres-url"
                    type="password"
                    placeholder="postgresql://user:password@localhost:5432/database"
                    value={postgresUrl}
                    onChange={(e) => setPostgresUrl(e.target.value)}
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    Enter the same PostgreSQL URL used by Evolution API to share the database.
                  </p>
                </div>

                {detectMutation.data && (
                  <Alert variant={detectMutation.data.found ? 'default' : 'destructive'}>
                    {detectMutation.data.found ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <AlertTriangle className="h-4 w-4" />
                    )}
                    <AlertTitle>
                      {detectMutation.data.found ? 'Evolution Database Detected' : 'Not Detected'}
                    </AlertTitle>
                    <AlertDescription>
                      {detectMutation.data.message}
                      {detectMutation.data.url_masked && (
                        <div className="mt-1 font-mono text-xs">
                          Detected URL: {detectMutation.data.url_masked}
                        </div>
                      )}
                    </AlertDescription>
                  </Alert>
                )}

                <div className="space-y-2">
                  <Button
                    onClick={handleTestConnection}
                    disabled={!postgresUrl || testMutation.isPending}
                    variant="secondary"
                    className="w-full"
                  >
                    {testMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Testing Connection...
                      </>
                    ) : (
                      <>
                        <Server className="h-4 w-4 mr-2" />
                        Test Connection
                      </>
                    )}
                  </Button>
                </div>

                {testResult && (
                  <div className="space-y-2 p-4 bg-muted rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">Connection Test Results</span>
                      <Badge variant={testResult.success ? 'default' : 'destructive'}>
                        {testResult.success ? 'All Passed' : 'Failed'}
                      </Badge>
                    </div>
                    <div className="space-y-1">
                      {Object.entries(testResult.tests).map(([name, result]) =>
                        renderTestResult(name, result)
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground pt-2">
                      Total time: {testResult.total_latency_ms.toFixed(0)}ms
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Redis Cache Configuration (Optional) */}
            <div className="border-t pt-4 mt-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <HardDrive className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <Label className="text-base font-semibold">Redis Cache (Optional)</Label>
                    <p className="text-xs text-muted-foreground">
                      Enable Redis caching for faster instance restarts and better performance
                    </p>
                  </div>
                </div>
                <Switch
                  checked={redisEnabled}
                  onCheckedChange={setRedisEnabled}
                />
              </div>

              {redisEnabled && (
                <div className="space-y-4 pl-7">
                  <div className="space-y-2">
                    <Label htmlFor="redis-url">Redis Connection URL</Label>
                    <Input
                      id="redis-url"
                      type="password"
                      placeholder="redis://localhost:6379/6"
                      value={redisUrl}
                      onChange={(e) => setRedisUrl(e.target.value)}
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground">
                      Redis URL for Evolution API cache (e.g., redis://localhost:6379/6)
                    </p>
                  </div>

                  <Button
                    onClick={handleTestRedisConnection}
                    disabled={!redisUrl || redisTestMutation.isPending}
                    variant="secondary"
                    className="w-full"
                  >
                    {redisTestMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Testing Redis Connection...
                      </>
                    ) : (
                      <>
                        <HardDrive className="h-4 w-4 mr-2" />
                        Test Redis Connection
                      </>
                    )}
                  </Button>

                  {redisTestResult && (
                    <div className="space-y-2 p-4 bg-muted rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">Redis Test Results</span>
                        <Badge variant={redisTestResult.success ? 'default' : 'destructive'}>
                          {redisTestResult.success ? 'All Passed' : 'Failed'}
                        </Badge>
                      </div>
                      <div className="space-y-1">
                        {Object.entries(redisTestResult.tests).map(([name, result]) =>
                          renderTestResult(name, result)
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground pt-2">
                        Total time: {redisTestResult.total_latency_ms.toFixed(0)}ms
                      </div>
                    </div>
                  )}

                  {/* Advanced Options */}
                  <Collapsible open={showAdvancedRedis} onOpenChange={setShowAdvancedRedis}>
                    <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                      {showAdvancedRedis ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                      Advanced options
                    </CollapsibleTrigger>
                    <CollapsibleContent className="space-y-4 pt-4">
                      <div className="space-y-2">
                        <Label htmlFor="redis-prefix">Key Prefix</Label>
                        <Input
                          id="redis-prefix"
                          type="text"
                          placeholder="evolution"
                          value={redisPrefixKey}
                          onChange={(e) => setRedisPrefixKey(e.target.value)}
                          className="font-mono"
                        />
                        <p className="text-xs text-muted-foreground">
                          Prefix for all Redis keys (default: evolution)
                        </p>
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
                          Time-to-live for cached data in seconds (default: 604800 = 7 days)
                        </p>
                      </div>

                      <div className="flex items-center justify-between">
                        <div>
                          <Label htmlFor="redis-save-instances">Save Instances in Redis</Label>
                          <p className="text-xs text-muted-foreground">
                            Store WhatsApp instance state in Redis for faster restarts
                          </p>
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

            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep('select')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button
                onClick={() => setStep('confirm')}
                disabled={!canProceedToConfirm}
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Confirm */}
        {step === 'confirm' && (
          <div className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Configuration Summary</AlertTitle>
              <AlertDescription className="space-y-2">
                <p>You are about to configure:</p>
                <ul className="list-disc list-inside text-sm">
                  <li>
                    Database Type: <strong>{dbType === 'sqlite' ? 'SQLite (Local)' : 'PostgreSQL (Shared)'}</strong>
                  </li>
                  {dbType === 'postgresql' && (
                    <>
                      <li>
                        Table Prefix: <code>omni_</code>
                      </li>
                      <li>Connection URL configured</li>
                    </>
                  )}
                  <li>
                    Redis Cache: <strong>{redisEnabled ? 'Enabled' : 'Disabled'}</strong>
                  </li>
                  {redisEnabled && (
                    <>
                      <li>Redis URL configured</li>
                      <li>
                        Key Prefix: <code>{redisPrefixKey}</code>
                      </li>
                      <li>TTL: {redisTtl} seconds</li>
                      <li>Save Instances: {redisSaveInstances ? 'Yes' : 'No'}</li>
                    </>
                  )}
                </ul>
                <p className="text-amber-600 dark:text-amber-400 font-medium pt-2">
                  Note: After saving, you will need to set environment variables and restart the application.
                </p>
              </AlertDescription>
            </Alert>

            {applyMutation.isSuccess && (
              <Alert className="bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertTitle className="text-green-600">Configuration Saved</AlertTitle>
                <AlertDescription className="text-green-600">
                  {applyMutation.data?.message}
                </AlertDescription>
              </Alert>
            )}

            {applyMutation.isError && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>
                  {(applyMutation.error as Error)?.message || 'Failed to save configuration'}
                </AlertDescription>
              </Alert>
            )}

            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep('configure')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button
                onClick={() => applyMutation.mutate()}
                disabled={applyMutation.isPending || applyMutation.isSuccess}
              >
                {applyMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : applyMutation.isSuccess ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Saved
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Save Configuration
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
