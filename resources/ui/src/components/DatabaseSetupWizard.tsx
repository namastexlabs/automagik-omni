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
  buildPostgresUrl,
  buildRedisUrl,
  type PostgresUrlComponents,
  type RedisUrlComponents,
} from '@/lib/database-url-utils';
import {
  useFieldValidation,
  validationRules,
  type ValidationState,
} from '@/hooks/useFieldValidation';
import { TestProgress } from '@/components/TestProgress';
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
  HardDrive,
  ChevronDown,
  ChevronRight,
  Check,
  Eye,
  EyeOff,
} from 'lucide-react';

type WizardStep = 'select' | 'configure' | 'confirm';

interface DatabaseSetupWizardProps {
  onComplete?: (config?: any) => void;
  isFirstRun?: boolean;
}

export function DatabaseSetupWizard({ onComplete, isFirstRun = false }: DatabaseSetupWizardProps) {
  const [step, setStep] = useState<WizardStep>('select');
  const [dbType, setDbType] = useState<'sqlite' | 'postgresql'>('sqlite');

  // PostgreSQL connection fields (individual) - empty by default, placeholders guide user
  const [pgHost, setPgHost] = useState('');
  const [pgPort, setPgPort] = useState('');
  const [pgUsername, setPgUsername] = useState('');
  const [pgPassword, setPgPassword] = useState('');
  const [pgDatabase, setPgDatabase] = useState('');
  const [testResult, setTestResult] = useState<DatabaseTestResponse | null>(null);

  // Redis connection fields (individual) - empty by default, placeholders guide user
  const [redisEnabled, setRedisEnabled] = useState(false);
  const [redisHost, setRedisHost] = useState('');
  const [redisPort, setRedisPort] = useState('');
  const [redisPassword, setRedisPassword] = useState('');
  const [redisDbNumber, setRedisDbNumber] = useState('0');
  const [redisTls, setRedisTls] = useState(false);
  const [redisPrefixKey, setRedisPrefixKey] = useState('evolution');
  const [redisTtl, setRedisTtl] = useState(604800);
  const [redisSaveInstances, setRedisSaveInstances] = useState(true);
  const [redisTestResult, setRedisTestResult] = useState<RedisTestResponse | null>(null);
  const [showAdvancedRedis, setShowAdvancedRedis] = useState(false);

  // Password visibility toggles
  const [showPgPassword, setShowPgPassword] = useState(false);
  const [showRedisPassword, setShowRedisPassword] = useState(false);

  // Field validation (PostgreSQL)
  const pgHostValidation = useFieldValidation(pgHost, validationRules.pgHost);
  const pgPortValidation = useFieldValidation(pgPort, validationRules.pgPort);
  const pgUsernameValidation = useFieldValidation(pgUsername, validationRules.pgUsername);
  const pgPasswordValidation = useFieldValidation(pgPassword, validationRules.pgPassword);
  const pgDatabaseValidation = useFieldValidation(pgDatabase, validationRules.pgDatabase);

  // Field validation (Redis)
  const redisHostValidation = useFieldValidation(redisHost, validationRules.redisHost);
  const redisPortValidation = useFieldValidation(redisPort, validationRules.redisPort);
  const redisPasswordValidation = useFieldValidation(redisPassword, validationRules.redisPassword);
  const redisDbNumberValidation = useFieldValidation(redisDbNumber, validationRules.redisDbNumber);

  // Fetch current config
  const { data: currentConfig, isLoading: configLoading } = useQuery({
    queryKey: ['database-config'],
    queryFn: () => api.database.getConfig(),
  });

  // Test connection
  const testMutation = useMutation({
    mutationFn: (url: string) => isFirstRun ? api.setup.testPostgresConnection(url) : api.database.testConnection(url),
    onSuccess: (data) => {
      setTestResult(data);
    },
  });

  // Test Redis connection
  const redisTestMutation = useMutation({
    mutationFn: (url: string) => isFirstRun ? api.setup.testRedisConnection(url) : api.database.testRedisConnection(url),
    onSuccess: (data) => {
      setRedisTestResult(data);
    },
  });

  // Apply configuration
  const applyMutation = useMutation({
    mutationFn: async () => {
      // Build URLs from individual fields
      let postgresUrl: string | undefined;
      let redisUrl: string | undefined;

      if (dbType === 'postgresql') {
        try {
          postgresUrl = buildPostgresUrl({
            host: pgHost,
            port: pgPort,
            username: pgUsername,
            password: pgPassword,
            database: pgDatabase,
          });
        } catch (error) {
          throw new Error(`Invalid PostgreSQL configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }

      if (redisEnabled) {
        try {
          redisUrl = buildRedisUrl({
            host: redisHost,
            port: redisPort,
            password: redisPassword,
            dbNumber: redisDbNumber,
            tls: redisTls,
          });
        } catch (error) {
          throw new Error(`Invalid Redis configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }

      if (isFirstRun) {
        // First-run mode: Just pass config up, don't call backend
        const config = {
          db_type: dbType,
          postgres_url: postgresUrl,
          redis_enabled: redisEnabled,
          redis_url: redisUrl,
          redis_prefix_key: redisPrefixKey,
          redis_ttl: redisTtl,
          redis_save_instances: redisSaveInstances,
        };
        return config;
      } else {
        // Settings mode: Call backend API as normal
        return api.database.apply(
          dbType,
          postgresUrl,
          {
            enabled: redisEnabled,
            url: redisUrl,
            prefixKey: redisPrefixKey,
            ttl: redisTtl,
            saveInstances: redisSaveInstances,
          }
        );
      }
    },
    onSuccess: (data) => {
      if (isFirstRun) {
        // Pass config to parent
        onComplete?.(data);
      } else {
        // Just call completion callback
        onComplete?.();
      }
    },
  });

  const handleTestConnection = () => {
    try {
      const postgresUrl = buildPostgresUrl({
        host: pgHost,
        port: pgPort,
        username: pgUsername,
        password: pgPassword,
        database: pgDatabase,
      });
      testMutation.mutate(postgresUrl);
    } catch (error) {
      console.error('Failed to build PostgreSQL URL:', error);
    }
  };

  const handleTestRedisConnection = () => {
    try {
      const redisUrl = buildRedisUrl({
        host: redisHost,
        port: redisPort,
        password: redisPassword,
        dbNumber: redisDbNumber,
        tls: redisTls,
      });
      redisTestMutation.mutate(redisUrl);
    } catch (error) {
      console.error('Failed to build Redis URL:', error);
    }
  };

  const canProceedToConfigure = dbType === 'sqlite' || (dbType === 'postgresql');
  const canProceedToConfirm =
    (dbType === 'sqlite' || testResult?.success === true) &&
    (!redisEnabled || redisTestResult?.success === true);

  // Helper: Get border color class based on validation state
  const getValidationClass = (state: ValidationState): string => {
    switch (state) {
      case 'valid':
        return 'border-green-500 focus-visible:ring-green-500';
      case 'invalid':
        return 'border-red-500 focus-visible:ring-red-500';
      case 'typing':
        return 'border-blue-500 focus-visible:ring-blue-500';
      default:
        return '';
    }
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
                  Share database with WhatsApp Web API. Uses <code>omni_</code> table prefix for isolation.
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
                <div className="space-y-4">
                  <div>
                    <Label className="text-base font-semibold">PostgreSQL Connection</Label>
                    <p className="text-sm text-muted-foreground mt-1">
                      Enter your PostgreSQL connection details. The database will be created if it doesn't exist.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="pg-host" className="flex items-center gap-2">
                        Host
                        {pgHostValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        {pgHostValidation.state === 'invalid' && (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </Label>
                      <Input
                        id="pg-host"
                        type="text"
                        placeholder="localhost"
                        value={pgHost}
                        onChange={(e) => setPgHost(e.target.value)}
                        className={getValidationClass(pgHostValidation.state)}
                      />
                      {pgHostValidation.error && (
                        <p className="text-xs text-red-500">{pgHostValidation.error}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pg-port" className="flex items-center gap-2">
                        Port
                        {pgPortValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        {pgPortValidation.state === 'invalid' && (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </Label>
                      <Input
                        id="pg-port"
                        type="text"
                        placeholder="5432"
                        value={pgPort}
                        onChange={(e) => setPgPort(e.target.value)}
                        className={getValidationClass(pgPortValidation.state)}
                      />
                      {pgPortValidation.error && (
                        <p className="text-xs text-red-500">{pgPortValidation.error}</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="pg-username" className="flex items-center gap-2">
                        Username
                        {pgUsernameValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        {pgUsernameValidation.state === 'invalid' && (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </Label>
                      <Input
                        id="pg-username"
                        type="text"
                        placeholder="postgres"
                        value={pgUsername}
                        onChange={(e) => setPgUsername(e.target.value)}
                        className={getValidationClass(pgUsernameValidation.state)}
                      />
                      {pgUsernameValidation.error && (
                        <p className="text-xs text-red-500">{pgUsernameValidation.error}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pg-password" className="flex items-center gap-2">
                        Password
                        {pgPasswordValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        {pgPasswordValidation.state === 'invalid' && (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </Label>
                      <div className="relative">
                        <Input
                          id="pg-password"
                          type={showPgPassword ? 'text' : 'password'}
                          placeholder="••••••••"
                          value={pgPassword}
                          onChange={(e) => setPgPassword(e.target.value)}
                          className={`${getValidationClass(pgPasswordValidation.state)} pr-10`}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3"
                          onClick={() => setShowPgPassword(!showPgPassword)}
                        >
                          {showPgPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {pgPasswordValidation.error && (
                        <p className="text-xs text-red-500">{pgPasswordValidation.error}</p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="pg-database" className="flex items-center gap-2">
                      Database Name
                      {pgDatabaseValidation.state === 'valid' && (
                        <Check className="h-3 w-3 text-green-500" />
                      )}
                      {pgDatabaseValidation.state === 'invalid' && (
                        <XCircle className="h-3 w-3 text-red-500" />
                      )}
                    </Label>
                    <Input
                      id="pg-database"
                      type="text"
                      placeholder="evolution"
                      value={pgDatabase}
                      onChange={(e) => setPgDatabase(e.target.value)}
                      className={getValidationClass(pgDatabaseValidation.state)}
                    />
                    {pgDatabaseValidation.error && (
                      <p className="text-xs text-red-500">{pgDatabaseValidation.error}</p>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Button
                    onClick={handleTestConnection}
                    disabled={!pgHost || !pgPort || !pgUsername || !pgPassword || !pgDatabase || testMutation.isPending}
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
                  <TestProgress
                    tests={testResult.tests}
                    totalLatency={testResult.total_latency_ms}
                    isPending={testMutation.isPending}
                    testType="postgresql"
                  />
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
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="redis-host" className="flex items-center gap-2">
                        Host
                        {redisHostValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        {redisHostValidation.state === 'invalid' && (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </Label>
                      <Input
                        id="redis-host"
                        type="text"
                        placeholder="localhost"
                        value={redisHost}
                        onChange={(e) => setRedisHost(e.target.value)}
                        className={getValidationClass(redisHostValidation.state)}
                      />
                      {redisHostValidation.error && (
                        <p className="text-xs text-red-500">{redisHostValidation.error}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="redis-port" className="flex items-center gap-2">
                        Port
                        {redisPortValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        {redisPortValidation.state === 'invalid' && (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </Label>
                      <Input
                        id="redis-port"
                        type="text"
                        placeholder="6379"
                        value={redisPort}
                        onChange={(e) => setRedisPort(e.target.value)}
                        className={getValidationClass(redisPortValidation.state)}
                      />
                      {redisPortValidation.error && (
                        <p className="text-xs text-red-500">{redisPortValidation.error}</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="redis-password" className="flex items-center gap-2">
                        Password (Optional)
                        {redisPasswordValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                      </Label>
                      <div className="relative">
                        <Input
                          id="redis-password"
                          type={showRedisPassword ? 'text' : 'password'}
                          placeholder="Leave empty if none"
                          value={redisPassword}
                          onChange={(e) => setRedisPassword(e.target.value)}
                          className={`${getValidationClass(redisPasswordValidation.state)} pr-10`}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full px-3"
                          onClick={() => setShowRedisPassword(!showRedisPassword)}
                        >
                          {showRedisPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {redisPasswordValidation.error && (
                        <p className="text-xs text-red-500">{redisPasswordValidation.error}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="redis-db" className="flex items-center gap-2">
                        Database Number
                        {redisDbNumberValidation.state === 'valid' && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        {redisDbNumberValidation.state === 'invalid' && (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </Label>
                      <Input
                        id="redis-db"
                        type="text"
                        placeholder="0"
                        value={redisDbNumber}
                        onChange={(e) => setRedisDbNumber(e.target.value)}
                        className={getValidationClass(redisDbNumberValidation.state)}
                      />
                      {redisDbNumberValidation.error && (
                        <p className="text-xs text-red-500">{redisDbNumberValidation.error}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="redis-tls">Use TLS (rediss://)</Label>
                      <p className="text-xs text-muted-foreground">
                        Enable secure connection with TLS/SSL
                      </p>
                    </div>
                    <Switch
                      id="redis-tls"
                      checked={redisTls}
                      onCheckedChange={setRedisTls}
                    />
                  </div>

                  <Button
                    onClick={handleTestRedisConnection}
                    disabled={!redisHost || !redisPort || !redisDbNumber || redisTestMutation.isPending}
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
                    <TestProgress
                      tests={redisTestResult.tests}
                      totalLatency={redisTestResult.total_latency_ms}
                      isPending={redisTestMutation.isPending}
                      testType="redis"
                    />
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
