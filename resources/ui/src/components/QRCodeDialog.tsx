import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { AlertCircle, QrCode as QrCodeIcon, RefreshCw, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface QRCodeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instanceName: string;
}

export function QRCodeDialog({ open, onOpenChange, instanceName }: QRCodeDialogProps) {
  const queryClient = useQueryClient();
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);

  // Fetch QR code with auto-refresh every 5 seconds
  const { data: qrData, isLoading: qrLoading, error: qrError, refetch: refetchQR } = useQuery({
    queryKey: ['qr-code', instanceName],
    queryFn: () => api.instances.getQR(instanceName),
    enabled: open,
    refetchInterval: open ? 5000 : false, // Auto-refresh every 5 seconds
    retry: 1,
  });

  // Poll connection status every 3 seconds while dialog is open
  const { data: statusData } = useQuery({
    queryKey: ['instance-status', instanceName],
    queryFn: () => api.instances.getStatus(instanceName),
    enabled: open,
    refetchInterval: open ? 3000 : false,
  });

  // Update QR image only when QR data changes (prevents flickering)
  useEffect(() => {
    if (qrData?.qr_code) {
      setQrImageUrl(qrData.qr_code);
    }
  }, [qrData?.qr_code]);

  // Check if connected using the correct field
  const isConnected = statusData?.connected === true || statusData?.status?.toLowerCase() === 'connected';

  // Auto-close dialog when connected
  useEffect(() => {
    if (isConnected && open) {
      // Invalidate instances query to refresh the list
      queryClient.invalidateQueries({ queryKey: ['instances'] });

      // Close after showing success message
      const timer = setTimeout(() => {
        onOpenChange(false);
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [isConnected, open, queryClient, onOpenChange]);

  const handleRefreshQR = () => {
    refetchQR();
  };

  // Get display status
  const displayStatus = statusData?.status || qrData?.status || 'Unknown';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <QrCodeIcon className="h-5 w-5 text-primary" />
            WhatsApp Connection
          </DialogTitle>
          <DialogDescription>
            {isConnected
              ? `Instance "${instanceName}" is now connected!`
              : `Scan this QR code with WhatsApp to connect "${instanceName}"`}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {/* Success State */}
          {isConnected && (
            <div className="flex flex-col items-center space-y-4 animate-fade-in">
              <div className="h-20 w-20 rounded-full gradient-success flex items-center justify-center elevation-lg">
                <CheckCircle2 className="h-12 w-12 text-white" />
              </div>
              <div className="text-center">
                <p className="text-lg font-semibold text-success mb-2">Successfully Connected!</p>
                <p className="text-sm text-muted-foreground">
                  WhatsApp is now connected and ready to use
                </p>
              </div>
              <Badge className="gradient-success border-0">Connected</Badge>
            </div>
          )}

          {/* Loading State */}
          {!isConnected && qrLoading && !qrImageUrl && (
            <div className="flex flex-col items-center space-y-4">
              <Skeleton className="h-64 w-64 rounded-lg" />
              <p className="text-sm text-muted-foreground">Loading QR code...</p>
            </div>
          )}

          {/* Error State */}
          {!isConnected && qrError && !qrImageUrl && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {qrError instanceof Error ? qrError.message : 'Failed to load QR code'}
              </AlertDescription>
            </Alert>
          )}

          {/* QR Code Display */}
          {!isConnected && qrImageUrl && (
            <div className="flex flex-col items-center space-y-4">
              <div className="p-4 bg-white rounded-lg elevation-md border-2 border-border">
                <img
                  src={qrImageUrl}
                  alt="WhatsApp QR Code"
                  className="w-64 h-64"
                  key={qrImageUrl} // Force re-render only when URL changes
                />
              </div>
              <div className="text-center space-y-2">
                <div className="flex items-center justify-center gap-2">
                  <p className="text-sm font-medium text-foreground">Status:</p>
                  <Badge variant="outline" className="capitalize">
                    {displayStatus}
                  </Badge>
                </div>
                {qrData?.message && (
                  <p className="text-xs text-muted-foreground">
                    {qrData.message}
                  </p>
                )}
                <p className="text-xs text-muted-foreground max-w-sm pt-2">
                  1. Open WhatsApp on your phone<br />
                  2. Go to Settings → Linked Devices<br />
                  3. Tap "Link a Device" and scan this code
                </p>
                <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground mt-3">
                  <div className="h-2 w-2 rounded-full bg-primary animate-pulse"></div>
                  <span>Waiting for scan... (Auto-refreshing every 5s)</span>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefreshQR}
                className="mt-2"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh QR Code
              </Button>
            </div>
          )}

          {/* No QR Code Available */}
          {!isConnected && qrData && !qrData.qr_code && !qrError && !qrLoading && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {qrData.message || 'No QR code available. The instance may already be connected or still initializing.'}
                <br />
                <br />
                Status: <span className="font-medium capitalize">{displayStatus}</span>
              </AlertDescription>
            </Alert>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
