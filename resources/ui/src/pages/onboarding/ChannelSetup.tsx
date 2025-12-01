import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import OnboardingLayout from '@/components/OnboardingLayout';
import { useOnboarding } from '@/contexts/OnboardingContext';
import { api } from '@/lib/api';
import {
  Loader2,
  MessageCircle,
  Bot,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Wifi,
  WifiOff,
  ChevronDown,
  ChevronUp,
  QrCode,
  Smartphone,
} from 'lucide-react';

interface ChannelStatus {
  enabled: boolean;
  configured: boolean;
  status: string;
  message?: string;
}

export default function ChannelSetup() {
  const navigate = useNavigate();
  const { completeSetup } = useOnboarding();

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidatingDiscord, setIsValidatingDiscord] = useState(false);

  // Channel status from backend
  const [whatsappStatus, setWhatsappStatus] = useState<ChannelStatus | null>(null);
  const [discordStatus, setDiscordStatus] = useState<ChannelStatus | null>(null);

  // Form state
  const [whatsappEnabled, setWhatsappEnabled] = useState(true);
  const [whatsappExpanded, setWhatsappExpanded] = useState(false);
  const [whatsappInstanceName, setWhatsappInstanceName] = useState('genie');
  const [whatsappAgentUrl, setWhatsappAgentUrl] = useState('');
  const [whatsappAgentKey, setWhatsappAgentKey] = useState('');

  // QR Code modal state
  const [showQrModal, setShowQrModal] = useState(false);
  const [qrCodeData, setQrCodeData] = useState<string | null>(null);
  const [qrInstanceName, setQrInstanceName] = useState<string | null>(null);

  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [discordExpanded, setDiscordExpanded] = useState(false);
  const [discordInstanceName, setDiscordInstanceName] = useState('');
  const [discordBotToken, setDiscordBotToken] = useState('');
  const [discordClientId, setDiscordClientId] = useState('');
  const [discordValidation, setDiscordValidation] = useState<{
    valid: boolean;
    bot_name?: string;
    message: string;
  } | null>(null);

  const [error, setError] = useState<string | null>(null);

  // Fetch channel status on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await api.setup.getChannelsStatus();
        setWhatsappStatus(status.whatsapp);
        setDiscordStatus(status.discord);
        setWhatsappEnabled(status.whatsapp.enabled);
        setDiscordEnabled(status.discord.enabled && status.discord.configured);
      } catch (err) {
        console.error('Failed to fetch channel status:', err);
        // Don't block setup on status fetch failure
      } finally {
        setIsLoading(false);
      }
    };

    fetchStatus();
  }, []);

  // Validate Discord token
  const handleValidateDiscord = async () => {
    if (!discordBotToken || !discordClientId) {
      setDiscordValidation({
        valid: false,
        message: 'Please enter both bot token and client ID',
      });
      return;
    }

    setIsValidatingDiscord(true);
    setDiscordValidation(null);

    try {
      const result = await api.setup.validateDiscordToken(discordBotToken, discordClientId);
      setDiscordValidation(result);
    } catch (err) {
      setDiscordValidation({
        valid: false,
        message: err instanceof Error ? err.message : 'Validation failed',
      });
    } finally {
      setIsValidatingDiscord(false);
    }
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Validate WhatsApp config if enabled and expanded (wants to create instance)
      if (whatsappEnabled && whatsappExpanded) {
        if (!whatsappInstanceName.trim()) {
          throw new Error('Please enter a WhatsApp instance name');
        }
        if (!whatsappAgentUrl.trim()) {
          throw new Error('Please enter your Agent API URL');
        }
        if (!whatsappAgentKey.trim()) {
          throw new Error('Please enter your Agent API Key');
        }
      }

      // Configure channels
      const result = await api.setup.configureChannels({
        whatsapp_enabled: whatsappEnabled,
        discord_enabled: discordEnabled,
        // WhatsApp instance params (only if expanded)
        whatsapp_instance_name: whatsappExpanded ? whatsappInstanceName : undefined,
        whatsapp_agent_api_url: whatsappExpanded ? whatsappAgentUrl : undefined,
        whatsapp_agent_api_key: whatsappExpanded ? whatsappAgentKey : undefined,
        // Discord params (simplified - just enable flag)
        discord_instance_name: undefined,
        discord_bot_token: undefined,
        discord_client_id: undefined,
      });

      // If we got a QR code, show the modal
      if (result.whatsapp_qr_code) {
        setQrCodeData(result.whatsapp_qr_code);
        setQrInstanceName(result.whatsapp_instance_name || whatsappInstanceName);
        setShowQrModal(true);
        // Don't navigate yet - wait for modal close
        return;
      }

      // Mark setup complete and navigate
      await api.setup.complete();
      await completeSetup();
      navigate('/dashboard');
    } catch (err) {
      console.error('Channel configuration failed:', err);
      setError(err instanceof Error ? err.message : 'Configuration failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle QR modal close - complete setup and navigate
  const handleQrModalClose = async () => {
    setShowQrModal(false);
    try {
      await api.setup.complete();
      await completeSetup();
      navigate('/dashboard');
    } catch (err) {
      console.error('Failed to complete setup:', err);
      // Navigate anyway - the important part (instance creation) is done
      navigate('/dashboard');
    }
  };

  // Skip channel setup (use defaults)
  const handleSkip = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      // Configure with defaults (WhatsApp only)
      await api.setup.configureChannels({
        whatsapp_enabled: true,
        discord_enabled: false,
      });

      // Mark setup complete
      await api.setup.complete();
      await completeSetup();

      // Navigate to dashboard
      navigate('/dashboard');
    } catch (err) {
      console.error('Skip failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to skip setup');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <OnboardingLayout currentStep={3} totalSteps={3} title="Channel Setup">
        <div className="p-8 flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 animate-spin text-purple-600 mb-4" />
          <p className="text-gray-600">Checking channel availability...</p>
        </div>
      </OnboardingLayout>
    );
  }

  return (
    <OnboardingLayout currentStep={3} totalSteps={3} title="Channel Setup">
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Communication Channels
          </h2>
          <p className="text-gray-600">
            Configure which messaging platforms you want to connect.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* WhatsApp Channel */}
          <div className={`rounded-lg border-2 transition-colors ${
            whatsappEnabled ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-gray-50'
          }`}>
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                    whatsappEnabled ? 'bg-green-500' : 'bg-gray-400'
                  }`}>
                    <MessageCircle className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">WhatsApp Web</h3>
                    <p className="text-sm text-gray-600">via WhatsApp Web API</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {whatsappStatus && (
                    <div className="flex items-center gap-1 text-sm">
                      {whatsappStatus.status === 'ready' ? (
                        <>
                          <Wifi className="h-4 w-4 text-green-500" />
                          <span className="text-green-600">Connected</span>
                        </>
                      ) : whatsappStatus.status === 'unavailable' ? (
                        <>
                          <WifiOff className="h-4 w-4 text-amber-500" />
                          <span className="text-amber-600">Not running</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-4 w-4 text-gray-400" />
                          <span className="text-gray-500">{whatsappStatus.message}</span>
                        </>
                      )}
                    </div>
                  )}
                  <Switch
                    checked={whatsappEnabled}
                    onCheckedChange={(checked) => {
                      setWhatsappEnabled(checked);
                      if (checked) setWhatsappExpanded(true);
                    }}
                  />
                </div>
              </div>

              {whatsappEnabled && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-2 w-full justify-between text-gray-600"
                  onClick={() => setWhatsappExpanded(!whatsappExpanded)}
                >
                  <span>{whatsappExpanded ? 'Hide' : 'Configure'} instance now</span>
                  {whatsappExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              )}
            </div>

            {/* WhatsApp Instance Configuration Form */}
            {whatsappEnabled && whatsappExpanded && (
              <div className="px-4 pb-4 space-y-4 border-t border-green-200">
                {/* Instructions */}
                <div className="mt-4 p-3 bg-green-100 rounded-lg">
                  <p className="text-sm text-green-800 mb-2 font-medium">
                    Create a WhatsApp instance now:
                  </p>
                  <ol className="text-sm text-green-700 space-y-1 list-decimal list-inside">
                    <li>Choose a name for your instance</li>
                    <li>Enter your AI agent's API URL and key</li>
                    <li>Scan the QR code with your phone to connect</li>
                  </ol>
                </div>

                {/* Instance Name */}
                <div className="space-y-2">
                  <Label htmlFor="whatsappInstanceName" className="text-gray-700">
                    Instance Name
                  </Label>
                  <Input
                    id="whatsappInstanceName"
                    type="text"
                    value={whatsappInstanceName}
                    onChange={(e) => setWhatsappInstanceName(e.target.value)}
                    placeholder="genie"
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500">
                    A unique name for this WhatsApp instance
                  </p>
                </div>

                {/* Agent API URL */}
                <div className="space-y-2">
                  <Label htmlFor="whatsappAgentUrl" className="text-gray-700">
                    Agent API URL
                  </Label>
                  <Input
                    id="whatsappAgentUrl"
                    type="text"
                    value={whatsappAgentUrl}
                    onChange={(e) => setWhatsappAgentUrl(e.target.value)}
                    placeholder="http://localhost:8000"
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500">
                    URL of your AI agent API (e.g., Automagik, OpenAI)
                  </p>
                </div>

                {/* Agent API Key */}
                <div className="space-y-2">
                  <Label htmlFor="whatsappAgentKey" className="text-gray-700">
                    Agent API Key
                  </Label>
                  <Input
                    id="whatsappAgentKey"
                    type="password"
                    value={whatsappAgentKey}
                    onChange={(e) => setWhatsappAgentKey(e.target.value)}
                    placeholder="sk-..."
                    className="bg-white font-mono"
                  />
                  <p className="text-xs text-gray-500">
                    Your agent API key (keep this private!)
                  </p>
                </div>
              </div>
            )}

            {whatsappEnabled && !whatsappExpanded && (
              <div className="px-4 pb-4 pt-2 border-t border-green-200">
                <p className="text-sm text-green-700">
                  You can create instances later in the dashboard.
                </p>
              </div>
            )}
          </div>

          {/* Discord Channel */}
          <div className={`rounded-lg border-2 transition-colors ${
            discordEnabled ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 bg-gray-50'
          }`}>
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                    discordEnabled ? 'bg-indigo-500' : 'bg-gray-400'
                  }`}>
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Discord</h3>
                    <p className="text-sm text-gray-600">Bot integration</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {discordStatus?.configured && (
                    <div className="flex items-center gap-1 text-sm">
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                      <span className="text-green-600">Configured</span>
                    </div>
                  )}
                  <Switch
                    checked={discordEnabled}
                    onCheckedChange={setDiscordEnabled}
                  />
                </div>
              </div>
              {discordEnabled && (
                <div className="mt-3 pt-3 border-t border-indigo-200">
                  <p className="text-sm text-indigo-700">
                    Discord bot configuration will be available in the Instances section after setup.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isSubmitting}
            className="w-full h-12 text-lg bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Completing Setup...
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 h-5 w-5" />
                Complete Setup
              </>
            )}
          </Button>
        </form>

        {/* Skip option */}
        <div className="mt-6 pt-6 border-t">
          <Button
            variant="outline"
            onClick={handleSkip}
            disabled={isSubmitting}
            className="w-full"
          >
            Skip - Use WhatsApp Only
          </Button>
          <p className="text-xs text-gray-500 text-center mt-2">
            You can add Discord later in the Instances settings.
          </p>
        </div>
      </div>

      {/* QR Code Modal */}
      <Dialog open={showQrModal} onOpenChange={(open) => !open && handleQrModalClose()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrCode className="h-5 w-5 text-green-600" />
              Connect WhatsApp
            </DialogTitle>
            <DialogDescription>
              Scan this QR code with your phone to connect {qrInstanceName || 'your instance'}.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center py-6">
            {qrCodeData ? (
              <>
                <div className="bg-white p-4 rounded-lg shadow-inner border">
                  <img
                    src={qrCodeData.startsWith('data:') ? qrCodeData : `data:image/png;base64,${qrCodeData}`}
                    alt="WhatsApp QR Code"
                    className="w-64 h-64"
                  />
                </div>
                <div className="mt-4 flex items-center gap-2 text-sm text-gray-600">
                  <Smartphone className="h-4 w-4" />
                  <span>Open WhatsApp on your phone and scan the code</span>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-green-600" />
                <p className="text-gray-600">Loading QR code...</p>
              </div>
            )}
          </div>
          <div className="flex justify-center">
            <Button onClick={handleQrModalClose} className="w-full">
              Continue to Dashboard
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </OnboardingLayout>
  );
}
