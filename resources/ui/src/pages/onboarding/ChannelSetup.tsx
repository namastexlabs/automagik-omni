import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
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
      // Validate Discord config if enabled
      if (discordEnabled) {
        if (!discordInstanceName.trim()) {
          throw new Error('Please enter a Discord instance name');
        }
        if (!discordBotToken.trim()) {
          throw new Error('Please enter your Discord bot token');
        }
        if (!discordClientId.trim()) {
          throw new Error('Please enter your Discord client ID');
        }
      }

      // Configure channels
      await api.setup.configureChannels({
        whatsapp_enabled: whatsappEnabled,
        discord_enabled: discordEnabled,
        discord_instance_name: discordEnabled ? discordInstanceName : undefined,
        discord_bot_token: discordEnabled ? discordBotToken : undefined,
        discord_client_id: discordEnabled ? discordClientId : undefined,
      });

      // Mark setup complete
      await api.setup.complete();
      await completeSetup();

      // Navigate to dashboard
      navigate('/dashboard');
    } catch (err) {
      console.error('Channel configuration failed:', err);
      setError(err instanceof Error ? err.message : 'Configuration failed');
    } finally {
      setIsSubmitting(false);
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
          <div className={`p-4 rounded-lg border-2 transition-colors ${
            whatsappEnabled ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-gray-50'
          }`}>
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
                  onCheckedChange={setWhatsappEnabled}
                />
              </div>
            </div>
            {whatsappEnabled && (
              <div className="mt-3 pt-3 border-t border-green-200">
                <p className="text-sm text-green-700">
                  WhatsApp uses your unified API key for authentication. Connect your phone in the Instances section after setup.
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
                    onCheckedChange={(checked) => {
                      setDiscordEnabled(checked);
                      if (checked) setDiscordExpanded(true);
                    }}
                  />
                </div>
              </div>

              {discordEnabled && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-2 w-full justify-between text-gray-600"
                  onClick={() => setDiscordExpanded(!discordExpanded)}
                >
                  <span>{discordExpanded ? 'Hide' : 'Show'} configuration</span>
                  {discordExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              )}
            </div>

            {/* Discord Configuration Form */}
            {discordEnabled && discordExpanded && (
              <div className="px-4 pb-4 space-y-4 border-t border-indigo-200">
                {/* Instructions */}
                <div className="mt-4 p-3 bg-indigo-100 rounded-lg">
                  <p className="text-sm text-indigo-800 mb-2 font-medium">
                    To set up a Discord bot:
                  </p>
                  <ol className="text-sm text-indigo-700 space-y-1 list-decimal list-inside">
                    <li>Go to Discord Developer Portal</li>
                    <li>Create a New Application</li>
                    <li>Go to "Bot" section and create a bot</li>
                    <li>Copy the bot token</li>
                    <li>Enable required intents (Message Content, etc.)</li>
                  </ol>
                  <a
                    href="https://discord.com/developers/applications"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 mt-2 text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    Open Discord Developer Portal
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                {/* Instance Name */}
                <div className="space-y-2">
                  <Label htmlFor="discordInstanceName" className="text-gray-700">
                    Instance Name
                  </Label>
                  <Input
                    id="discordInstanceName"
                    type="text"
                    value={discordInstanceName}
                    onChange={(e) => setDiscordInstanceName(e.target.value)}
                    placeholder="my-discord-bot"
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500">
                    A unique name for this Discord instance
                  </p>
                </div>

                {/* Client ID */}
                <div className="space-y-2">
                  <Label htmlFor="discordClientId" className="text-gray-700">
                    Application Client ID
                  </Label>
                  <Input
                    id="discordClientId"
                    type="text"
                    value={discordClientId}
                    onChange={(e) => setDiscordClientId(e.target.value)}
                    placeholder="123456789012345678"
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500">
                    Found in your application's "General Information"
                  </p>
                </div>

                {/* Bot Token */}
                <div className="space-y-2">
                  <Label htmlFor="discordBotToken" className="text-gray-700">
                    Bot Token
                  </Label>
                  <Input
                    id="discordBotToken"
                    type="password"
                    value={discordBotToken}
                    onChange={(e) => setDiscordBotToken(e.target.value)}
                    placeholder="MTIzNDU2Nzg5MDEy..."
                    className="bg-white font-mono"
                  />
                  <p className="text-xs text-gray-500">
                    Your bot's secret token (keep this private!)
                  </p>
                </div>

                {/* Validate Button */}
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleValidateDiscord}
                    disabled={isValidatingDiscord || !discordBotToken || !discordClientId}
                  >
                    {isValidatingDiscord ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Validating...
                      </>
                    ) : (
                      'Test Connection'
                    )}
                  </Button>

                  {discordValidation && (
                    <div className={`flex items-center gap-2 text-sm ${
                      discordValidation.valid ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {discordValidation.valid ? (
                        <>
                          <CheckCircle2 className="h-4 w-4" />
                          <span>Bot: {discordValidation.bot_name}</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-4 w-4" />
                          <span>{discordValidation.message}</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
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
    </OnboardingLayout>
  );
}
