import { useState, useEffect, useRef } from 'react';
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
import { useLogStream } from '@/hooks/useLogStream';
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

  // Log streaming for Evolution startup
  const logContainerRef = useRef<HTMLDivElement>(null);
  const {
    logs: evolutionLogs,
    isConnected: logsConnected,
    connect: connectLogs,
    disconnect: disconnectLogs,
    clearLogs,
  } = useLogStream({
    services: ['evolution'],
    maxLogs: 50,
    autoConnect: false, // Manual control during startup
  });

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

  // Auto-scroll log viewer during startup
  useEffect(() => {
    if (logContainerRef.current && evolutionStarting) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [evolutionLogs, evolutionStarting]);

  // Handle WhatsApp toggle - starts Evolution when enabled
  const handleWhatsAppToggle = async (enabled: boolean) => {
    setWhatsappEnabled(enabled);
    setEvolutionError(null);

    // If enabling and Evolution is not ready, start it
    if (enabled && !evolutionReady) {
      setEvolutionStarting(true);
      clearLogs();
      connectLogs();

      try {
        await api.gateway.startChannel('evolution');
        const ready = await api.gateway.waitForChannel('evolution', 60000);
        if (ready) {
          setEvolutionReady(true);
        } else {
          setEvolutionError('WhatsApp service started but is not responding. Please try again.');
        }
      } catch (err) {
        console.error('Failed to start Evolution:', err);
        setEvolutionError(err instanceof Error ? err.message : 'Failed to start WhatsApp service');
      } finally {
        setEvolutionStarting(false);
        disconnectLogs();
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

      // Start Evolution if WhatsApp enabled and not running
      if (whatsappEnabled && !evolutionReady) {
        setEvolutionStarting(true);
        clearLogs();
        connectLogs();

        try {
          await api.gateway.startChannel('evolution');
          const ready = await api.gateway.waitForChannel('evolution', 120000);
          if (!ready) {
            throw new Error('WhatsApp service failed to start. Please try again.');
          }
          setEvolutionReady(true);
        } finally {
          setEvolutionStarting(false);
          disconnectLogs();
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

                {/* Starting indicator with logs */}
                {evolutionStarting && (
                  <div className="mt-4 p-4 bg-green-100 rounded-lg">
                    <div className="flex items-center gap-3 mb-3">
                      <Loader2 className="h-6 w-6 text-green-600 animate-spin" />
                      <div>
                        <p className="text-sm text-green-800 font-medium">Starting WhatsApp service...</p>
                        <p className="text-xs text-green-700">This may take up to a minute</p>
                      </div>
                    </div>
                    {evolutionLogs.length > 0 && (
                      <div
                        ref={logContainerRef}
                        className="bg-gray-900 rounded-lg p-3 max-h-32 overflow-y-auto font-mono text-xs"
                      >
                        {evolutionLogs.map((log, i) => (
                          <div
                            key={i}
                            className={`py-0.5 ${
                              log.level === 'error' ? 'text-red-400' :
                              log.level === 'warn' ? 'text-yellow-400' :
                              'text-green-400'
                            }`}
                          >
                            <span className="text-gray-500">
                              {log.timestamp.split('T')[1]?.slice(0, 8)}
                            </span>
                            {' '}
                            <span>{log.message}</span>
                          </div>
                        ))}
                      </div>
                    )}
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
    </OnboardingLayout>
  );
}
