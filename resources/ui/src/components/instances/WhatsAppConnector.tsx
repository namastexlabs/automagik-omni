import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  MessageCircle,
  RefreshCw,
} from 'lucide-react';

interface WhatsAppConnectorProps {
  instanceName: string;
  onBack: () => void;
  onSuccess: () => void;
}

type ConnectionPhase = 'creating' | 'starting' | 'qr' | 'connected' | 'error';

export function WhatsAppConnector({ instanceName, onBack, onSuccess }: WhatsAppConnectorProps) {
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<ConnectionPhase>('creating');
  const [error, setError] = useState<string | null>(null);
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);
  const [instanceCreated, setInstanceCreated] = useState(false);

  // Create instance mutation
  const createMutation = useMutation({
    mutationFn: () => api.instances.create({
      name: instanceName,
      channel_type: 'whatsapp',
    }),
    onSuccess: () => {
      setInstanceCreated(true);
      setPhase('starting');
      toast.success(`Connection "${instanceName}" created`);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create connection');
      setPhase('error');
    },
  });

  // Create instance on mount
  useEffect(() => {
    if (!instanceCreated) {
      createMutation.mutate();
    }
  }, []);

  // Fetch QR code with auto-refresh
  const { data: qrData, isLoading: qrLoading, error: qrError, refetch: refetchQR } = useQuery({
    queryKey: ['qr-code', instanceName],
    queryFn: () => api.instances.getQR(instanceName),
    enabled: instanceCreated && phase !== 'connected' && phase !== 'error',
    refetchInterval: phase === 'qr' || phase === 'starting' ? 5000 : false,
    retry: 3,
    retryDelay: 2000,
  });

  // Poll connection status
  const { data: statusData } = useQuery({
    queryKey: ['instance-status', instanceName],
    queryFn: () => api.instances.getStatus(instanceName),
    enabled: instanceCreated && phase !== 'connected' && phase !== 'error',
    refetchInterval: 3000,
  });

  // Update QR image when data changes
  useEffect(() => {
    if (qrData?.qr_code) {
      setQrImageUrl(qrData.qr_code);
      if (phase === 'starting') {
        setPhase('qr');
      }
    }
  }, [qrData?.qr_code, phase]);

  // Check if connected
  const isConnected = statusData?.connected === true ||
                      statusData?.status?.toLowerCase() === 'connected';

  // Handle connection success
  useEffect(() => {
    if (isConnected && phase !== 'connected') {
      setPhase('connected');
      queryClient.invalidateQueries({ queryKey: ['instances'] });

      // Auto-close after showing success
      setTimeout(() => {
        onSuccess();
      }, 2000);
    }
  }, [isConnected, phase, queryClient, onSuccess]);

  // Handle QR error after retries
  useEffect(() => {
    if (qrError && phase === 'starting') {
      // Keep trying, QR might not be ready yet
    }
  }, [qrError, phase]);

  const handleRefreshQR = () => {
    refetchQR();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="h-14 w-14 rounded-2xl bg-[#25D366] flex items-center justify-center mx-auto">
          <MessageCircle className="h-6 w-6 text-white" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            {phase === 'connected' ? 'Connected!' : 'Connect WhatsApp'}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {phase === 'creating' && 'Setting up your connection...'}
            {phase === 'starting' && 'Starting WhatsApp service...'}
            {phase === 'qr' && 'Scan this QR code with your phone'}
            {phase === 'connected' && `"${instanceName}" is now connected`}
            {phase === 'error' && 'Something went wrong'}
          </p>
        </div>
      </div>

      {/* Progress Indicator */}
      {(phase === 'creating' || phase === 'starting') && (
        <div className="flex flex-col items-center space-y-4 py-8">
          <Loader2 className="h-12 w-12 animate-spin text-[#25D366]" />
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">
              {phase === 'creating' ? 'Creating connection...' : 'Loading QR code...'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              This may take a few seconds
            </p>
          </div>
        </div>
      )}

      {/* Success State */}
      {phase === 'connected' && (
        <div className="flex flex-col items-center space-y-4 py-8 animate-fade-in">
          <div className="h-20 w-20 rounded-full bg-[#25D366] flex items-center justify-center">
            <CheckCircle2 className="h-12 w-12 text-white" />
          </div>
          <div className="text-center">
            <p className="text-lg font-semibold text-[#25D366] mb-2">Successfully Connected!</p>
            <p className="text-sm text-muted-foreground">
              WhatsApp is now ready to use
            </p>
          </div>
          <Badge className="bg-[#25D366] border-0">Connected</Badge>
        </div>
      )}

      {/* Error State */}
      {phase === 'error' && (
        <div className="space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || 'Failed to set up connection'}</AlertDescription>
          </Alert>
          <div className="flex gap-3">
            <Button variant="outline" onClick={onBack} className="flex-1">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Go Back
            </Button>
            <Button
              onClick={() => {
                setPhase('creating');
                setError(null);
                createMutation.mutate();
              }}
              className="flex-1"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        </div>
      )}

      {/* QR Code Display */}
      {phase === 'qr' && qrImageUrl && (
        <div className="flex flex-col items-center space-y-4">
          <div className="p-4 bg-white rounded-lg border-2 border-border">
            <img
              src={qrImageUrl}
              alt="WhatsApp QR Code"
              className="w-56 h-56"
              data-testid="qr-code"
              key={qrImageUrl}
            />
          </div>

          <div className="text-center space-y-3">
            <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
              <div className="h-2 w-2 rounded-full bg-[#25D366] animate-pulse"></div>
              <span>Waiting for scan...</span>
            </div>

            <div className="text-xs text-muted-foreground max-w-xs">
              <p className="font-medium text-foreground mb-2">How to connect:</p>
              <ol className="text-left space-y-1">
                <li>1. Open WhatsApp on your phone</li>
                <li>2. Go to Settings → Linked Devices</li>
                <li>3. Tap "Link a Device" and scan</li>
              </ol>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshQR}
              className="mt-2"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh QR
            </Button>
          </div>
        </div>
      )}

      {/* Loading QR skeleton */}
      {phase === 'qr' && !qrImageUrl && qrLoading && (
        <div className="flex flex-col items-center space-y-4">
          <Skeleton className="h-56 w-56 rounded-lg" />
          <p className="text-sm text-muted-foreground">Loading QR code...</p>
        </div>
      )}

      {/* Back button (only when not in success state) */}
      {phase !== 'connected' && phase !== 'error' && (
        <div className="pt-2">
          <Button variant="ghost" onClick={onBack} className="w-full">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>
      )}
    </div>
  );
}
