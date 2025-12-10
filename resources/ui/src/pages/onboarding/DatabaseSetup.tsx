import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { DatabaseSetupWizard } from '@/components/DatabaseSetupWizard';
import { DatabaseStartupModal } from '@/components/DatabaseStartupModal';
import OnboardingLayout from '@/components/OnboardingLayout';
import { api, removeApiKey } from '@/lib/api';
import { DatabaseConfig } from '@/types/onboarding';
import { Loader2 } from 'lucide-react';

type StartupPhase = 'idle' | 'checking' | 'pgserve' | 'python' | 'saving' | 'done' | 'error';

// Check if pgserve is healthy
async function checkPgserveHealth(timeoutMs: number = 3000): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const response = await fetch('/health/pgserve', { signal: controller.signal });
    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      return data.status === 'healthy'; // pgserve returns { status: 'healthy' }
    }
  } catch {
    // Not available
  }
  return false;
}

// Check if Python API is healthy via gateway
// IMPORTANT: Only check services.python.status, NOT top-level status (which is gateway status)
async function checkPythonHealth(timeoutMs: number = 3000): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const response = await fetch('/health', { signal: controller.signal });
    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      // ONLY check Python-specific status - data.status is gateway status, not Python!
      const pythonStatus = data.services?.python?.status;
      const isUp = pythonStatus === 'up';
      console.log('[DatabaseSetup] Python health check:', { pythonStatus, isUp });
      return isUp;
    }
    console.log('[DatabaseSetup] Python health check: response not ok');
  } catch (err) {
    console.log('[DatabaseSetup] Python health check error:', err);
  }
  return false;
}

// Poll until pgserve is healthy
async function pollUntilPgserveHealthy(timeoutMs: number = 30000): Promise<void> {
  const startTime = Date.now();
  const pollInterval = 1000;

  while (Date.now() - startTime < timeoutMs) {
    if (await checkPgserveHealth()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
  }
  throw new Error('PostgreSQL did not become healthy within timeout');
}

// Poll until Python is healthy
async function pollUntilPythonHealthy(timeoutMs: number = 30000): Promise<void> {
  const startTime = Date.now();
  const pollInterval = 1000;

  while (Date.now() - startTime < timeoutMs) {
    if (await checkPythonHealth()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
  }
  throw new Error('Python API did not become healthy within timeout');
}

export default function DatabaseSetup() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [startupPhase, setStartupPhase] = useState<StartupPhase>('idle');
  const [showStartupModal, setShowStartupModal] = useState(false);
  const [pendingConfig, setPendingConfig] = useState<DatabaseConfig | null>(null);
  const [isCheckingServices, setIsCheckingServices] = useState(true);

  // Check if services are already running on mount
  useEffect(() => {
    const checkExistingServices = async () => {
      setIsCheckingServices(true);

      try {
        // Check if both pgserve and python API are already healthy
        const [pgserveHealthy, pythonHealthy] = await Promise.all([checkPgserveHealth(), checkPythonHealth()]);

        if (pgserveHealthy && pythonHealthy) {
          // Services already running - navigate directly to next step
          console.log('[DatabaseSetup] Services already running, navigating to api-key');
          navigate('/onboarding/api-key');
          return;
        }
      } catch (err) {
        console.log('[DatabaseSetup] Error checking services:', err);
        // Continue with normal setup flow
      }

      setIsCheckingServices(false);
    };

    checkExistingServices();
  }, [navigate]);

  // Clear any stale API key and setup state from previous installations
  // This ensures fresh installs don't retain old localStorage data
  useEffect(() => {
    removeApiKey();
    localStorage.removeItem('omni_setup_complete');
  }, []);

  const startServices = useCallback(async (config: DatabaseConfig) => {
    try {
      setError(null);
      setStartupPhase('checking');
      console.log('[DatabaseSetup] Starting services with config:', config);

      // First, check what's already running
      // NOTE: Use specific health check functions that check the correct status fields
      const [pgserveHealthy, pythonHealthy] = await Promise.all([checkPgserveHealth(), checkPythonHealth()]);
      console.log('[DatabaseSetup] Initial health check:', { pgserveHealthy, pythonHealthy });

      // If everything is already running, skip to done
      if (pgserveHealthy && pythonHealthy) {
        console.log('[DatabaseSetup] All services already healthy - skipping to done');
        setStartupPhase('done');
        return;
      }

      // Phase 1: Start PostgreSQL (if not already running)
      if (!pgserveHealthy) {
        console.log('[DatabaseSetup] Phase 1: Starting PostgreSQL...');
        setStartupPhase('pgserve');

        // Write pgserve config BEFORE starting pgserve
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
        console.log('[DatabaseSetup] pgserve config written');

        // Start PostgreSQL
        const pgserveResponse = await fetch('/api/internal/services/pgserve/start', { method: 'POST' });
        console.log('[DatabaseSetup] pgserve start response:', pgserveResponse.status);
        if (!pgserveResponse.ok) {
          const errorData = await pgserveResponse.json();
          throw new Error(errorData.error || 'Failed to start PostgreSQL');
        }

        // Wait for PostgreSQL to become healthy
        console.log('[DatabaseSetup] Waiting for pgserve to become healthy...');
        await pollUntilPgserveHealthy(30000);
        console.log('[DatabaseSetup] pgserve is now healthy');
      } else {
        console.log('[DatabaseSetup] pgserve already healthy, skipping');
      }

      // Phase 2: Start Python API (if not already running)
      if (!pythonHealthy) {
        console.log('[DatabaseSetup] Phase 2: Starting Python API...');
        setStartupPhase('python');

        const pythonResponse = await fetch('/api/internal/services/python/start', { method: 'POST' });
        console.log('[DatabaseSetup] Python start response:', pythonResponse.status);
        if (!pythonResponse.ok) {
          const errorData = await pythonResponse.json();
          throw new Error(errorData.error || 'Failed to start API server');
        }

        // Wait for Python to become healthy
        console.log('[DatabaseSetup] Waiting for Python to become healthy...');
        await pollUntilPythonHealthy(30000);
        console.log('[DatabaseSetup] Python is now healthy');
      } else {
        console.log('[DatabaseSetup] python already healthy, skipping');
      }

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

  // Show loading while checking services
  if (isCheckingServices) {
    return (
      <OnboardingLayout currentStep={1} totalSteps={4} title="Welcome to Automagik Omni">
        <div className="p-8 flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 animate-spin text-purple-600 mb-4" />
          <p className="text-gray-600">Checking services...</p>
        </div>
      </OnboardingLayout>
    );
  }

  return (
    <OnboardingLayout currentStep={1} totalSteps={4} title="Welcome to Automagik Omni">
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
