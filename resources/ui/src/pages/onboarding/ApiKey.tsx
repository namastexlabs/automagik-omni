import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import OnboardingLayout from '@/components/OnboardingLayout';
import { setApiKey as saveApiKey, api } from '@/lib/api';
import { Loader2, CheckCircle2, Copy, Check, AlertTriangle, Key } from 'lucide-react';

export default function ApiKey() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);

  // Fetch auto-generated API key on mount and save to localStorage
  useEffect(() => {
    const fetchApiKey = async () => {
      try {
        const result = await api.setup.getApiKey();
        if (result.api_key) {
          setGeneratedKey(result.api_key);
          // Auto-save to localStorage immediately
          saveApiKey(result.api_key);
        }
      } catch (err) {
        console.error('Setup API key fetch failed:', err);
        const errorMsg = err instanceof Error ? err.message : '';

        // If setup is already complete, try recovery endpoint (localhost-only)
        if (errorMsg.includes('Setup already completed') || errorMsg.includes('403')) {
          try {
            const recoveryResult = await api.recovery.getApiKey();
            if (recoveryResult.api_key) {
              setGeneratedKey(recoveryResult.api_key);
              saveApiKey(recoveryResult.api_key);
              return;
            }
          } catch (recoveryErr) {
            console.error('Recovery API key fetch failed:', recoveryErr);
            const recoveryMsg = recoveryErr instanceof Error ? recoveryErr.message : '';

            if (recoveryMsg.includes('localhost') || recoveryMsg.includes('403')) {
              setError(
                'Setup is complete. To recover your API key, access this page from the server machine (localhost) ' +
                  'or check your database: SELECT value FROM omni_global_settings WHERE key="omni_api_key"',
              );
            } else {
              setError('Could not retrieve API key. Please check the server logs.');
            }
            return;
          }
        }

        setError('Could not retrieve API key. Please try refreshing the page.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchApiKey();
  }, []);

  const handleCopy = async () => {
    if (generatedKey) {
      await navigator.clipboard.writeText(generatedKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleContinue = async () => {
    setIsSubmitting(true);
    // Key is already saved to localStorage, just navigate
    navigate('/onboarding/channels');
  };

  if (isLoading) {
    return (
      <OnboardingLayout currentStep={2} totalSteps={4} title="API Key">
        <div className="p-8 flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 animate-spin text-purple-600 mb-4" />
          <p className="text-gray-600">Generating your API key...</p>
        </div>
      </OnboardingLayout>
    );
  }

  return (
    <OnboardingLayout currentStep={2} totalSteps={4} title="API Key">
      <div className="p-8">
        <div className="mb-6 text-center">
          <div className="flex justify-center mb-4">
            <div className="h-12 w-12 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center">
              <Key className="h-6 w-6 text-white" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Your API Key</h2>
          <p className="text-gray-600">Save this key securely - you'll need it to access Automagik Omni</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm font-medium">{error}</p>
          </div>
        )}

        {generatedKey && (
          <div className="mb-6">
            {/* Warning */}
            <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-amber-800 text-sm font-medium">Save this key now!</p>
                <p className="text-amber-700 text-xs mt-1">
                  Store it somewhere safe. You can use it to access the API from other tools.
                </p>
              </div>
            </div>

            {/* API Key Display */}
            <div className="relative">
              <div className="p-4 bg-gray-900 rounded-lg font-mono text-sm text-green-400 break-all pr-12">
                {generatedKey}
              </div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white hover:bg-gray-700"
                onClick={handleCopy}
              >
                {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        )}

        <Button
          onClick={handleContinue}
          disabled={isSubmitting || !generatedKey}
          className="w-full h-12 text-lg bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading...
            </>
          ) : (
            <>
              <CheckCircle2 className="mr-2 h-5 w-5" />
              I've Saved My Key - Continue
            </>
          )}
        </Button>

        <p className="mt-4 text-xs text-gray-500 text-center">You'll stay logged in on this browser.</p>
      </div>
    </OnboardingLayout>
  );
}
