import { useState, useEffect } from 'react';
import { flushSync } from 'react-dom';
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
import { EvolutionStartupModal } from '@/components/EvolutionStartupModal';
import {
  Loader2,
  MessageCircle,
  Bot,
  CheckCircle2,
  AlertCircle,
  Wifi,
  WifiOff,
  QrCode,
  Smartphone,
  Terminal,
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

  // Evolution startup states
  const [evolutionStarting, setEvolutionStarting] = useState(false);
  const [evolutionReady, setEvolutionReady] = useState(false);
  const [evolutionError, setEvolutionError] = useState<string | null>(null);

  // Form state
  const [whatsappEnabled, setWhatsappEnabled] = useState(true);
  const [whatsappInstanceName, setWhatsappInstanceName] = useState('genie');
  const [discordEnabled, setDiscordEnabled] = useState(false);

  // QR Code modal state
  const [showQrModal, setShowQrModal] = useState(false);
  const [qrCodeData, setQrCodeData] = useState<string | null>(null);
  const [qrInstanceName, setQrInstanceName] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  // Evolution startup modal state
  const [showStartupModal, setShowStartupModal] = useState(false);

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

  // Handle WhatsApp toggle - just track state, don't start Evolution yet
  // Evolution will start on "Complete Setup" AFTER database config is saved
  const handleWhatsAppToggle = (enabled: boolean) => {
    setWhatsappEnabled(enabled);
    setEvolutionError(null);
    // Don't start Evolution here - DB config may not exist yet
    // Evolution will be started in handleSubmit when user clicks "Complete Setup"
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

      // Start Evolution if WhatsApp enabled and not running
      if (whatsappEnabled && !evolutionReady) {
        // Force synchronous render so modal is visible BEFORE any API errors
        flushSync(() => {
          setEvolutionStarting(true);
          setShowStartupModal(true);
        });

        // Additional delay for SSE connection to establish
        await new Promise(r => setTimeout(r, 150));

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
                  headers: { apikey: api_key }
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
              await new Promise(r => setTimeout(r, 1000));
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

      // Configure channels
      const result = await api.setup.configureChannels({
        whatsapp_enabled: whatsappEnabled,
        discord_enabled: discordEnabled,
        whatsapp_instance_name: whatsappEnabled ? whatsappInstanceName : undefined,
      });

      // If we got a QR code, show the modal
      if (result.whatsapp_qr_code) {
        setQrCodeData(result.whatsapp_qr_code);
        setQrInstanceName(result.whatsapp_instance_name || whatsappInstanceName);
        setShowQrModal(true);
        return;
      }

      // Check if WhatsApp is already connected (instance exists in Evolution from before wipe)
      if (result.whatsapp_status?.startsWith('connected:')) {
        // Already connected! Skip QR code and proceed to completion
        console.log('WhatsApp already connected, skipping QR code step');
        await api.setup.complete();
        await completeSetup();
        navigate('/dashboard');
        return;
      }

      // If WhatsApp was enabled but no QR code returned, that's an error
      // The instance was created but Evolution failed to generate QR
      if (whatsappEnabled && result.whatsapp_instance_name && !result.whatsapp_qr_code) {
        // Check if status indicates pending connection (Evolution not ready)
        if (result.whatsapp_status?.includes('pending_connection')) {
          // It might be that the instance is created but QR generation was slow
          // Try to fetch QR one more time before erroring
          try {
            const qrResult = await api.instances.getQR(result.whatsapp_instance_name);
            if (qrResult.qr_code) {
               setQrCodeData(qrResult.qr_code);
               setQrInstanceName(result.whatsapp_instance_name);
               setShowQrModal(true);
               return;
            }
          } catch (e) {
            // ignore and show original error
          }

          setEvolutionError('WhatsApp service is not ready. Please wait a moment and try again.');
          setShowStartupModal(true);
          setIsSubmitting(false);
          return;
        }

        setEvolutionError('Failed to get QR code. WhatsApp service may not be running.');
        setShowStartupModal(true);
        setIsSubmitting(false);
        return;
      }

      // Mark setup complete and navigate (only if WhatsApp was disabled or skipped)
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

        {/* Only show error when modal is NOT open - modal is primary feedback */}
        {error && !showStartupModal && (
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
                      headers: { apikey: api_key }
                    });
                    if (res.status !== 502 && res.status !== 503 && res.status !== 504) {
                      apiReady = true;
                      break;
                    }
                  } catch (e) { /* ignore */ }
                  await new Promise(r => setTimeout(r, 1000));
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
    </OnboardingLayout>
  );
}
