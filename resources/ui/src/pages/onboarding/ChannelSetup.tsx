import { useState, useEffect } from 'react';
import { flushSync } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import OnboardingLayout from '@/components/OnboardingLayout';
import { useOnboarding } from '@/contexts/OnboardingContext';
import { api } from '@/lib/api';
import { EvolutionStartupModal } from '@/components/EvolutionStartupModal';
import { QRCodeDialog } from '@/components/QRCodeDialog';
import { DiscordInstallModal } from '@/components/DiscordInstallModal';
import { WhatsAppConfigModal } from '@/components/WhatsAppConfigModal';
import { Loader2, MessageCircle, Bot, CheckCircle2, AlertCircle, Wifi, WifiOff, Terminal } from 'lucide-react';

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

  // Evolution startup states
  const [evolutionStarting, setEvolutionStarting] = useState(false);
  const [evolutionReady, setEvolutionReady] = useState(false);
  const [evolutionError, setEvolutionError] = useState<string | null>(null);

  // Form state - channels default to OFF, user must explicitly enable them
  const [whatsappEnabled, setWhatsappEnabled] = useState(false);
  const [whatsappInstanceName, setWhatsappInstanceName] = useState('genie');
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [discordInstanceName, setDiscordInstanceName] = useState('discord-bot');
  const [discordClientId, setDiscordClientId] = useState('');
  const [discordBotToken, setDiscordBotToken] = useState('');

  // Discord installation states
  const [discordInstalled, setDiscordInstalled] = useState<boolean | null>(null);
  const [showDiscordInstallModal, setShowDiscordInstallModal] = useState(false);
  const [discordCheckingInstall, setDiscordCheckingInstall] = useState(false);

  // QR Code modal state
  const [showQrModal, setShowQrModal] = useState(false);
  const [qrInstanceName, setQrInstanceName] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  // Evolution startup modal state
  const [showStartupModal, setShowStartupModal] = useState(false);

  // WhatsApp config modal state (opens on switch toggle)
  const [showWhatsAppModal, setShowWhatsAppModal] = useState(false);

  // Track if instance was created in modal (to skip duplicate creation in form submit)
  const [instanceCreatedInModal, setInstanceCreatedInModal] = useState(false);

  // Check if Evolution is already running on mount
  useEffect(() => {
    const checkEvolution = async () => {
      try {
        const gatewayStatus = await api.gateway.getStatus();
        const evolutionProc = gatewayStatus.processes?.evolution;
        if (evolutionProc?.healthy) {
          setEvolutionReady(true);
        }
      } catch (e) {
        // Gateway not available yet - that's OK
      } finally {
        setIsLoading(false);
      }
    };

    checkEvolution();
  }, []);

  // Auto-open startup modal on error
  useEffect(() => {
    if (evolutionError) setShowStartupModal(true);
  }, [evolutionError]);

  // Handle WhatsApp toggle - open configuration modal (like Discord does)
  const handleWhatsAppToggle = (enabled: boolean) => {
    setWhatsappEnabled(enabled);
    setEvolutionError(null);

    if (enabled) {
      // Open configuration modal (same pattern as Discord)
      setShowWhatsAppModal(true);
    }
  };

  // Handle Discord toggle - check if discord.py is installed
  const handleDiscordToggle = async (enabled: boolean) => {
    setDiscordEnabled(enabled);

    if (enabled) {
      // Check if Discord is installed
      setDiscordCheckingInstall(true);
      try {
        const status = await api.gateway.checkDiscordInstalled();
        setDiscordInstalled(status.installed);

        if (!status.installed) {
          // Show installation modal
          setShowDiscordInstallModal(true);
        }
      } catch (err) {
        console.error('Failed to check Discord installation:', err);
        // Assume not installed if check fails
        setDiscordInstalled(false);
        setShowDiscordInstallModal(true);
      } finally {
        setDiscordCheckingInstall(false);
      }
    }
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Validate WhatsApp instance name if enabled
      if (whatsappEnabled && !whatsappInstanceName.trim()) {
        throw new Error('Please enter a WhatsApp instance name');
      }

      // Validate Discord inputs if enabled
      if (discordEnabled) {
        // Check if Discord is installed first
        if (!discordInstalled) {
          setShowDiscordInstallModal(true);
          throw new Error('Discord support needs to be installed first');
        }
        if (!discordInstanceName.trim()) {
          throw new Error('Please enter a Discord instance name');
        }
        if (!discordClientId.trim()) {
          throw new Error('Please enter your Discord Application Client ID');
        }
        if (!/^\d{17,20}$/.test(discordClientId.trim())) {
          throw new Error('Discord Client ID should be a 17-20 digit number');
        }
        if (!discordBotToken.trim()) {
          throw new Error('Please enter your Discord bot token');
        }
        if (discordBotToken.length < 50) {
          throw new Error("This doesn't look like a valid Discord bot token");
        }
      }

      // Start Evolution if WhatsApp enabled and not running
      if (whatsappEnabled && !evolutionReady) {
        // Force synchronous render so modal is visible BEFORE any API errors
        flushSync(() => {
          setEvolutionStarting(true);
          setShowStartupModal(true);
        });

        // Additional delay for SSE connection to establish
        await new Promise((r) => setTimeout(r, 150));

        try {
          await api.gateway.startChannel('evolution');
          const ready = await api.gateway.waitForChannel('evolution', 120000);
          if (!ready) {
            // Don't throw - route to modal error state so user sees logs
            setEvolutionError('WhatsApp service failed to start. Check logs above.');
            setIsSubmitting(false);
            return; // Modal stays open with logs visible
          }

          // Wait for API to be actually responsive (process running != API ready)
          let apiReady = false;
          try {
            // Get API key for the probe request
            const { api_key } = await api.setup.getApiKey();

            // Probe the API for up to 30 seconds
            for (let i = 0; i < 30; i++) {
              try {
                // Use fetch directly to avoid the api wrapper's error handling
                const res = await fetch('/evolution/instance/fetchInstances', {
                  headers: { apikey: api_key },
                });

                // If we get a valid response (even 404/400), the API is up
                // 502/503/504 means the proxy target is not reachable yet
                if (res.status !== 502 && res.status !== 503 && res.status !== 504) {
                  apiReady = true;
                  break;
                }
              } catch (e) {
                // ignore connection errors
              }
              await new Promise((r) => setTimeout(r, 1000));
            }
          } catch (e) {
            console.warn('Failed to check API readiness:', e);
            // Continue anyway, maybe it will work
            apiReady = true;
          }

          if (!apiReady) {
            setEvolutionError('WhatsApp service started but API is not responding. Please check logs.');
            setIsSubmitting(false);
            return;
          }

          setEvolutionReady(true);
        } catch (err) {
          // Route to modal error state, don't throw to main catch
          setEvolutionError(err instanceof Error ? err.message : 'Failed to start service');
          setIsSubmitting(false);
          return; // Modal stays open with logs visible
        } finally {
          setEvolutionStarting(false);
        }
      }

      // If WhatsApp instance was already created in the modal, skip configureChannels for WhatsApp
      // Just configure Discord if needed
      if (instanceCreatedInModal && whatsappEnabled) {
        // WhatsApp already configured in modal - just handle Discord if enabled
        if (discordEnabled && discordClientId && discordBotToken) {
          try {
            await api.instances.create({
              name: discordInstanceName,
              channel_type: 'discord',
              discord_bot_token: discordBotToken,
              discord_client_id: discordClientId,
            });
          } catch (err) {
            console.error('Failed to create Discord instance:', err);
            // Continue anyway - WhatsApp is already set up
          }
        }

        // Mark setup complete and navigate
        await api.setup.complete();
        await completeSetup();
        navigate('/dashboard');
        return;
      }

      // Configure channels (WhatsApp instance not created in modal)
      const result = await api.setup.configureChannels({
        whatsapp_enabled: whatsappEnabled,
        discord_enabled: discordEnabled,
        whatsapp_instance_name: whatsappEnabled ? whatsappInstanceName : undefined,
      });

      // If instance was created OR already exists (connected), show the QR modal
      // QRCodeDialog handles both states: shows QR if disconnected, shows "Connected!" if connected
      // This ensures Discord setup always happens via handleQrModalClose
      if (result.whatsapp_instance_name || result.whatsapp_status?.startsWith('connected:')) {
        setQrInstanceName(result.whatsapp_instance_name || whatsappInstanceName);
        setShowQrModal(true);
        return;
      }

      // If WhatsApp was enabled but instance not created, that's an error
      if (whatsappEnabled && !result.whatsapp_instance_name) {
        // Check if status indicates pending connection (Evolution not ready)
        if (result.whatsapp_status?.includes('pending_connection')) {
          setEvolutionError('WhatsApp service is not ready. Please wait a moment and try again.');
          setShowStartupModal(true);
          setIsSubmitting(false);
          return;
        }

        setEvolutionError('Failed to create WhatsApp instance. Service may not be running.');
        setShowStartupModal(true);
        setIsSubmitting(false);
        return;
      }

      // Create Discord instance if enabled (WhatsApp was disabled, so no QR modal flow)
      if (discordEnabled && discordClientId && discordBotToken) {
        try {
          await api.instances.create({
            name: discordInstanceName,
            channel_type: 'discord',
            discord_bot_token: discordBotToken,
            discord_client_id: discordClientId,
          });
        } catch (err) {
          console.error('Failed to create Discord instance:', err);
          // Continue anyway
        }
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

  // Handle QR modal close - create Discord instance if needed, complete setup and navigate
  const handleQrModalClose = async () => {
    setShowQrModal(false);
    try {
      // Create Discord instance if enabled
      if (discordEnabled && discordClientId && discordBotToken) {
        try {
          await api.instances.create({
            name: discordInstanceName,
            channel_type: 'discord',
            discord_bot_token: discordBotToken,
            discord_client_id: discordClientId,
          });
        } catch (err) {
          console.error('Failed to create Discord instance:', err);
          // Continue anyway - WhatsApp is already set up
        }
      }

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
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Communication Channels</h2>
          <p className="text-gray-600">Configure which messaging platforms you want to connect.</p>
        </div>

        {/* Only show error when modal is NOT open - modal is primary feedback */}
        {error && !showStartupModal && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* WhatsApp Channel */}
          <div
            className={`rounded-lg border-2 transition-colors ${
              whatsappEnabled ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-gray-50'
            }`}
          >
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                      whatsappEnabled ? 'bg-green-500' : 'bg-gray-400'
                    }`}
                  >
                    <MessageCircle className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">WhatsApp Web</h3>
                    <p className="text-sm text-gray-600">Connect via QR code</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {evolutionStarting ? (
                    <div className="flex items-center gap-1 text-sm">
                      <Loader2 className="h-4 w-4 text-green-500 animate-spin" />
                      <span className="text-green-600">Starting...</span>
                    </div>
                  ) : evolutionReady ? (
                    <div className="flex items-center gap-1 text-sm">
                      <Wifi className="h-4 w-4 text-green-500" />
                      <span className="text-green-600">Ready</span>
                    </div>
                  ) : whatsappEnabled ? (
                    <div className="flex items-center gap-1 text-sm">
                      <WifiOff className="h-4 w-4 text-amber-500" />
                      <span className="text-amber-600">Will start</span>
                    </div>
                  ) : null}
                  <Switch
                    checked={whatsappEnabled}
                    onCheckedChange={handleWhatsAppToggle}
                    disabled={evolutionStarting}
                  />
                </div>
              </div>
            </div>

            {/* WhatsApp Instance Configuration - always visible when enabled */}
            {whatsappEnabled && (
              <div className="px-4 pb-4 space-y-4 border-t border-green-200">
                {/* Error display */}
                {evolutionError && (
                  <div className="mt-4 p-3 bg-red-100 rounded-lg flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-red-800 font-medium">Failed to start WhatsApp service</p>
                      <p className="text-sm text-red-700">{evolutionError}</p>
                    </div>
                  </div>
                )}

                {/* Starting indicator with View Logs button */}
                {evolutionStarting && (
                  <div className="mt-4 p-4 bg-green-100 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Loader2 className="h-6 w-6 text-green-600 animate-spin" />
                        <div>
                          <p className="text-sm text-green-800 font-medium">Starting WhatsApp service...</p>
                          <p className="text-xs text-green-700">This may take up to a minute</p>
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowStartupModal(true)}
                        className="border-green-600 text-green-700 hover:bg-green-50"
                      >
                        <Terminal className="h-4 w-4 mr-1" />
                        View Logs
                      </Button>
                    </div>
                  </div>
                )}

                {/* Instance Name - always visible when enabled, not starting */}
                {!evolutionStarting && (
                  <div className="mt-4 space-y-2">
                    <Label htmlFor="whatsappInstanceName" className="text-gray-700">
                      Instance Name
                    </Label>
                    <Input
                      id="whatsappInstanceName"
                      type="text"
                      value={whatsappInstanceName}
                      onChange={(e) => setWhatsappInstanceName(e.target.value)}
                      placeholder="genie"
                    />
                    <p className="text-xs text-gray-500">
                      {evolutionReady
                        ? "Click 'Complete Setup' to create this instance and scan QR code"
                        : "Service will start automatically when you click 'Complete Setup'"}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Discord Channel */}
          <div
            className={`rounded-lg border-2 transition-colors ${
              discordEnabled ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 bg-gray-50'
            }`}
          >
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                      discordEnabled ? 'bg-indigo-500' : 'bg-gray-400'
                    }`}
                  >
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Discord</h3>
                    <p className="text-sm text-gray-600">Bot integration</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {discordCheckingInstall ? (
                    <div className="flex items-center gap-1 text-sm">
                      <Loader2 className="h-4 w-4 text-indigo-500 animate-spin" />
                      <span className="text-indigo-600">Checking...</span>
                    </div>
                  ) : discordEnabled && discordInstalled ? (
                    <div className="flex items-center gap-1 text-sm">
                      <Wifi className="h-4 w-4 text-green-500" />
                      <span className="text-green-600">Ready</span>
                    </div>
                  ) : discordEnabled && discordInstalled === false ? (
                    <div className="flex items-center gap-1 text-sm">
                      <WifiOff className="h-4 w-4 text-amber-500" />
                      <span className="text-amber-600">Not installed</span>
                    </div>
                  ) : null}
                  <Switch
                    checked={discordEnabled}
                    onCheckedChange={handleDiscordToggle}
                    disabled={discordCheckingInstall}
                  />
                </div>
              </div>
              {discordEnabled && (
                <div className="px-4 pb-4 space-y-4 border-t border-indigo-200">
                  {/* Show install prompt if not installed */}
                  {discordInstalled === false && (
                    <div className="mt-4 p-3 bg-amber-100 rounded-lg flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm text-amber-800 font-medium">Discord support not installed</p>
                        <p className="text-sm text-amber-700">Click below to install the required dependencies.</p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowDiscordInstallModal(true)}
                          className="mt-2 border-amber-600 text-amber-700 hover:bg-amber-50"
                        >
                          <Terminal className="h-4 w-4 mr-1" />
                          Install Discord Support
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Only show form fields if installed */}
                  {discordInstalled && (
                    <>
                      <div className="mt-4 space-y-2">
                        <Label htmlFor="discordInstanceName" className="text-gray-700">
                          Instance Name
                        </Label>
                        <Input
                          id="discordInstanceName"
                          type="text"
                          value={discordInstanceName}
                          onChange={(e) => setDiscordInstanceName(e.target.value)}
                          placeholder="discord-bot"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="discordClientId" className="text-gray-700">
                          Application Client ID
                        </Label>
                        <Input
                          id="discordClientId"
                          type="text"
                          value={discordClientId}
                          onChange={(e) => setDiscordClientId(e.target.value)}
                          placeholder="e.g. 123456789012345678"
                          className="font-mono text-sm"
                        />
                        <p className="text-xs text-gray-500">
                          Found in Discord Developer Portal → Your Application → General Information
                        </p>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="discordBotToken" className="text-gray-700">
                          Bot Token
                        </Label>
                        <Input
                          id="discordBotToken"
                          type="password"
                          value={discordBotToken}
                          onChange={(e) => setDiscordBotToken(e.target.value)}
                          placeholder="Enter your Discord bot token"
                          className="font-mono text-sm"
                        />
                        <p className="text-xs text-gray-500">Found in Discord Developer Portal → Bot → Reset Token</p>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isSubmitting || evolutionStarting}
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
          <Button variant="outline" onClick={handleSkip} disabled={isSubmitting} className="w-full">
            Skip - Use WhatsApp Only
          </Button>
          <p className="text-xs text-gray-500 text-center mt-2">You can add Discord later in the Instances settings.</p>
        </div>
      </div>

      {/* QR Code Modal - uses QRCodeDialog which has status polling and auto-close on connection */}
      {qrInstanceName && (
        <QRCodeDialog
          open={showQrModal}
          onOpenChange={(open) => {
            if (!open) {
              handleQrModalClose();
            }
          }}
          instanceName={qrInstanceName}
        />
      )}

      {/* Evolution Startup Modal */}
      <EvolutionStartupModal
        open={showStartupModal}
        onOpenChange={setShowStartupModal}
        externalError={evolutionError}
        onSuccess={() => {
          setEvolutionReady(true);
          setShowStartupModal(false);
        }}
        onRetry={() => {
          setEvolutionError(null);
          setEvolutionStarting(true);

          // Full retry sequence: Start -> Wait Process -> Wait API
          const retrySequence = async () => {
            try {
              await api.gateway.startChannel('evolution');
              const ready = await api.gateway.waitForChannel('evolution', 120000);

              if (!ready) {
                throw new Error('WhatsApp service failed to start');
              }

              // Wait for API to be actually responsive
              let apiReady = false;
              try {
                const { api_key } = await api.setup.getApiKey();
                for (let i = 0; i < 30; i++) {
                  try {
                    const res = await fetch('/evolution/instance/fetchInstances', {
                      headers: { apikey: api_key },
                    });
                    if (res.status !== 502 && res.status !== 503 && res.status !== 504) {
                      apiReady = true;
                      break;
                    }
                  } catch (e) {
                    /* ignore */
                  }
                  await new Promise((r) => setTimeout(r, 1000));
                }
              } catch (e) {
                apiReady = true; // optimistic fallthrough
              }

              if (!apiReady) {
                throw new Error('WhatsApp service started but API is not responding');
              }

              setEvolutionReady(true);
              setShowStartupModal(false); // Close modal so user can click "Complete Setup"
            } catch (err) {
              setEvolutionError(err instanceof Error ? err.message : 'Failed to start service');
            } finally {
              setEvolutionStarting(false);
            }
          };

          retrySequence();
        }}
      />

      {/* Discord Install Modal */}
      <DiscordInstallModal
        open={showDiscordInstallModal}
        onOpenChange={(open) => {
          setShowDiscordInstallModal(open);
          // If user closes without success, disable Discord
          if (!open && !discordInstalled) {
            setDiscordEnabled(false);
          }
        }}
        onSuccess={() => {
          setDiscordInstalled(true);
          setShowDiscordInstallModal(false);
        }}
        onRetry={() => {
          // Modal handles retry internally
        }}
      />

      {/* WhatsApp Config Modal - opens on switch toggle */}
      <WhatsAppConfigModal
        open={showWhatsAppModal}
        onOpenChange={(open) => {
          setShowWhatsAppModal(open);
          // If user closes without connecting, disable WhatsApp
          if (!open && !evolutionReady) {
            setWhatsappEnabled(false);
          }
        }}
        instanceName={whatsappInstanceName}
        onSuccess={() => {
          setEvolutionReady(true);
          setShowWhatsAppModal(false);
        }}
        onInstanceCreated={(name) => {
          setInstanceCreatedInModal(true);
          setWhatsappInstanceName(name);
        }}
      />
    </OnboardingLayout>
  );
}
