import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DatabaseSetupWizard } from '@/components/DatabaseSetupWizard';
import OnboardingLayout from '@/components/OnboardingLayout';
import { api, removeApiKey } from '@/lib/api';
import { DatabaseConfig } from '@/types/onboarding';
import { Loader2 } from 'lucide-react';

export default function DatabaseSetup() {
  const navigate = useNavigate();
  const [isSkipping, setIsSkipping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clear any stale API key and setup state from previous installations
  // This ensures fresh installs don't retain old localStorage data
  useEffect(() => {
    removeApiKey();
    localStorage.removeItem('omni_setup_complete');
  }, []);

  const handleWizardComplete = async (wizardConfig: DatabaseConfig) => {
    try {
      setError(null);

      // Initialize backend with config
      await api.setup.initialize(wizardConfig);

      // Move to API key step
      navigate('/onboarding/api-key');
    } catch (err) {
      console.error('Setup initialization failed:', err);
      setError(err instanceof Error ? err.message : 'Setup initialization failed');
    }
  };

  const handleSkip = async () => {
    try {
      setIsSkipping(true);
      setError(null);

      // Initialize with SQLite defaults
      await api.setup.initialize({
        db_type: 'sqlite',
        redis_enabled: false,
      });

      // Move to API key step
      navigate('/onboarding/api-key');
    } catch (err) {
      console.error('Skip setup failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to skip setup');
    } finally {
      setIsSkipping(false);
    }
  };

  return (
    <OnboardingLayout
      currentStep={1}
      totalSteps={3}
      title="Welcome to Automagik Omni"
    >
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Database Configuration
          </h2>
          <p className="text-gray-600">
            Choose your database backend. You can change this later in Settings.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        <DatabaseSetupWizard
          onComplete={handleWizardComplete}
          isFirstRun={true}
        />

        <div className="mt-6 pt-6 border-t">
          <Button
            variant="outline"
            onClick={handleSkip}
            disabled={isSkipping}
            className="w-full"
          >
            {isSkipping ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Skipping...
              </>
            ) : (
              'Skip - Use SQLite Defaults'
            )}
          </Button>
          <p className="text-xs text-gray-500 text-center mt-2">
            SQLite is perfect for getting started. You can configure PostgreSQL later.
          </p>
        </div>
      </div>
    </OnboardingLayout>
  );
}
