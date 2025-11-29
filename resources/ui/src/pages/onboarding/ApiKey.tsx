import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import OnboardingLayout from '@/components/OnboardingLayout';
import { useOnboarding } from '@/contexts/OnboardingContext';
import { setApiKey as saveApiKey, api } from '@/lib/api';
import { Lock, Loader2, CheckCircle2 } from 'lucide-react';

export default function ApiKey() {
  const navigate = useNavigate();
  const { completeSetup } = useOnboarding();
  const [apiKey, setApiKey] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsValidating(true);
    setError(null);

    try {
      // Save API key to localStorage
      saveApiKey(apiKey);

      // Give a tiny delay to ensure localStorage is written
      await new Promise(resolve => setTimeout(resolve, 50));

      // Test authentication
      const isValid = await api.testAuth();

      if (isValid) {
        // Mark setup complete in backend
        await api.setup.complete();

        // Update context
        await completeSetup();

        // Navigate to dashboard
        navigate('/dashboard');
      } else {
        setError('Invalid API key. Please check and try again.');
        // Clear invalid key from localStorage
        localStorage.removeItem('omni_api_key');
      }
    } catch (err) {
      console.error('API key validation failed:', err);
      setError(err instanceof Error ? err.message : 'Authentication failed');
      // Clear invalid key from localStorage
      localStorage.removeItem('omni_api_key');
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <OnboardingLayout
      currentStep={2}
      totalSteps={2}
      title="API Key"
    >
      <div className="p-8">
        <div className="mb-6 text-center">
          <div className="flex justify-center mb-4">
            <div className="h-12 w-12 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center">
              <Lock className="h-6 w-6 text-white" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Enter Your API Key
          </h2>
          <p className="text-gray-600">
            Your API key is required to use Automagik Omni
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm font-medium">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="apiKey" className="text-gray-700 font-medium">
              API Key
            </Label>
            <Input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              required
              className="h-12 text-lg"
              autoFocus
            />
            <p className="text-xs text-gray-500">
              Enter your Automagik API key to continue
            </p>
          </div>

          <Button
            type="submit"
            disabled={isValidating || !apiKey.trim()}
            className="w-full h-12 text-lg bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
          >
            {isValidating ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Validating...
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 h-5 w-5" />
                Continue to Dashboard
              </>
            )}
          </Button>
        </form>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            Your API key is stored securely in your browser's local storage.
          </p>
        </div>
      </div>
    </OnboardingLayout>
  );
}
