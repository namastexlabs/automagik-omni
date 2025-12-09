import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { DatabaseSetupWizard } from '@/components/DatabaseSetupWizard';
import { DatabaseStartupModal } from '@/components/DatabaseStartupModal';
import OnboardingLayout from '@/components/OnboardingLayout';
import { api, removeApiKey } from '@/lib/api';
import { DatabaseConfig } from '@/types/onboarding';
import { Loader2 } from 'lucide-react';

type StartupPhase = 'idle' | 'pgserve' | 'python' | 'saving' | 'done' | 'error';

// Helper to poll until a service is healthy
async function pollUntilHealthy(endpoint: string, timeoutMs: number = 30000): Promise<void> {
  const startTime = Date.now();
  const pollInterval = 1000;

  while (Date.now() - startTime < timeoutMs) {
    try {
      const response = await fetch(endpoint);
      if (response.ok) {
        const data = await response.json();
        // Check for health indicators
        // Accept 'degraded' too - means Python is up but optional services (Evolution) aren't
        if (
          data.status === 'healthy' ||
          data.status === 'up' ||
          data.status === 'degraded' ||
          data.services?.python?.status === 'up' ||
          data.services?.api?.status === 'up'
        ) {
          return;
        }
      }
    } catch {
      // Service not ready yet, continue polling
    }
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
  }
  throw new Error(`Service at ${endpoint} did not become healthy within ${timeoutMs}ms`);
}

export default function DatabaseSetup() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [startupPhase, setStartupPhase] = useState<StartupPhase>('idle');
  const [showStartupModal, setShowStartupModal] = useState(false);
  const [pendingConfig, setPendingConfig] = useState<DatabaseConfig | null>(null);

  // Clear any stale API key and setup state from previous installations
  // This ensures fresh installs don't retain old localStorage data
  useEffect(() => {
    const clearStaleData = async () => {
      await removeApiKey();
      localStorage.removeItem('omni_setup_complete');
    };
    clearStaleData();
  }, []);

  const handleWizardComplete = async (wizardConfig: DatabaseConfig) => {
    // Store config and open modal
    setPendingConfig(wizardConfig);
    setShowStartupModal(true);
    setError(null);
    setStartupPhase('idle');

    // Start the actual services
    await startServices(wizardConfig);
  };

  const startServices = async (config: DatabaseConfig) => {
    try {
      setError(null);

      // Phase 0: Write pgserve config BEFORE starting pgserve
      // This ensures memory mode is respected on first start
      setStartupPhase('pgserve');
      const configResponse = await fetch('/api/internal/pgserve-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          memory_mode: config.memory_mode ?? false,
          data_dir: config.data_dir,
          replication_url: config.replication_enabled ? config.replication_url : null,
        }),
      });
      if (!configResponse.ok) {
        const errorData = await configResponse.json();
        throw new Error(errorData.error || 'Failed to write PostgreSQL config');
      }

      // Phase 1: Start PostgreSQL (now config exists)
      const pgserveResponse = await fetch('/api/internal/services/pgserve/start', { method: 'POST' });
      if (!pgserveResponse.ok) {
        const errorData = await pgserveResponse.json();
        throw new Error(errorData.error || 'Failed to start PostgreSQL');
      }

      // Wait for PostgreSQL to become healthy
      await pollUntilHealthy('/health/pgserve', 30000);

      // Phase 2: Start Python API
      setStartupPhase('python');
      const pythonResponse = await fetch('/api/internal/services/python/start', { method: 'POST' });
      if (!pythonResponse.ok) {
        const errorData = await pythonResponse.json();
        throw new Error(errorData.error || 'Failed to start API server');
      }

      // Wait for Python to become healthy
      await pollUntilHealthy('/health', 30000);

      // Phase 3: Save configuration
      setStartupPhase('saving');
      await api.setup.initialize(config);

      // Done!
      setStartupPhase('done');
    } catch (err) {
      console.error('Setup initialization failed:', err);
      setError(err instanceof Error ? err.message : 'Setup initialization failed');
      setStartupPhase('error');
    }
  };

  const handleRetry = () => {
    if (pendingConfig) {
      setError(null);
      setStartupPhase('idle');
      startServices(pendingConfig);
    }
  };

  const handleStartupSuccess = () => {
    setShowStartupModal(false);
    navigate('/onboarding/api-key');
  };

  const handleSkip = async () => {
    // Use default config and same startup sequence
    await handleWizardComplete({
      data_dir: './data/postgres',
      memory_mode: false,
      replication_enabled: false,
      redis_enabled: false,
    });
  };

  return (
    <OnboardingLayout currentStep={1} totalSteps={3} title="Welcome to Automagik Omni">
      <DatabaseStartupModal
        open={showStartupModal}
        onOpenChange={setShowStartupModal}
        onSuccess={handleStartupSuccess}
        onRetry={handleRetry}
        externalError={error}
        currentPhase={startupPhase}
      />
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Storage Configuration</h2>
          <p className="text-gray-600">
            Configure PostgreSQL storage for your data. You can adjust these settings later.
          </p>
        </div>

        {error && startupPhase === 'idle' && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        <DatabaseSetupWizard onComplete={handleWizardComplete} isFirstRun={true} />

        <div className="mt-6 pt-6 border-t">
          <Button variant="outline" onClick={handleSkip} disabled={showStartupModal} className="w-full">
            {showStartupModal ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Initializing...
              </>
            ) : (
              'Skip - Use Default Storage'
            )}
          </Button>
          <p className="text-xs text-gray-500 text-center mt-2">
            Default storage uses embedded PostgreSQL with persistent disk storage.
          </p>
        </div>
      </div>
    </OnboardingLayout>
  );
}
