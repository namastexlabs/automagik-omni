import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  LogOut,
  QrCode,
  Loader2,
  User,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { api } from '@/lib';

interface ConnectionSheetProps {
  instanceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConnectionSheet({ instanceName, open, onOpenChange }: ConnectionSheetProps) {
  const [showQR, setShowQR] = useState(false);
  const queryClient = useQueryClient();

  // Fetch instance details
  const { data: instance } = useQuery({
    queryKey: ['instance', instanceName],
    queryFn: () => api.instances.get(instanceName),
    enabled: open,
  });

  // Connection state query
  const { data: connectionState, isLoading: isLoadingState } = useQuery({
    queryKey: ['connection-state', instanceName],
    queryFn: () => api.evolution.getConnectionState(instanceName),
    refetchInterval: open ? 5000 : false,
    enabled: open,
  });

  // QR code query
  const { data: qrData, isLoading: isLoadingQR, refetch: refetchQR } = useQuery({
    queryKey: ['qr-code', instanceName],
    queryFn: () => api.instances.getQR(instanceName),
    enabled: open && showQR && connectionState?.state !== 'open',
    refetchInterval: showQR && connectionState?.state !== 'open' ? 5000 : false,
  });

  // Restart mutation
  const restartMutation = useMutation({
    mutationFn: () => api.evolution.restart(instanceName),
    onSuccess: () => {
      toast.success('Instance restarted');
      queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to restart: ${error.message}`);
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: () => api.evolution.logout(instanceName),
    onSuccess: () => {
      toast.success('Logged out');
      queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to logout: ${error.message}`);
    },
  });

  const state = connectionState?.state || instance?.evolution_status?.state || 'unknown';
  const isConnected = state === 'open';
  const isConnecting = state === 'connecting';

  const profile = instance?.evolution_status || {};

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Wifi className="h-5 w-5" />
            Connection - {instanceName}
          </SheetTitle>
          <SheetDescription>
            Manage connection status and authentication
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] mt-6">
          <div className="space-y-6 pr-4">
            {/* Status */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
              <span className="text-sm font-medium">Status</span>
              <Badge
                variant={isConnected ? 'default' : 'secondary'}
                className={isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500' : 'bg-red-500'}
              >
                {isLoadingState ? (
                  <><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Checking...</>
                ) : isConnected ? (
                  <><Wifi className="h-3 w-3 mr-1" /> Connected</>
                ) : isConnecting ? (
                  <><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Connecting</>
                ) : (
                  <><WifiOff className="h-3 w-3 mr-1" /> Disconnected</>
                )}
              </Badge>
            </div>

            {/* Profile */}
            <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
              <Avatar className="h-16 w-16">
                <AvatarImage src={profile.profile_picture_url || instance?.profile_pic_url || undefined} />
                <AvatarFallback>
                  <User className="h-8 w-8" />
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate text-lg">
                  {profile.profile_name || instance?.profile_name || instanceName}
                </p>
                <p className="text-sm text-muted-foreground truncate">
                  {profile.owner_jid || instance?.owner_jid || 'No number connected'}
                </p>
              </div>
            </div>

            {/* QR Code Section */}
            {!isConnected && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Authentication</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowQR(!showQR)}
                  >
                    <QrCode className="h-4 w-4 mr-2" />
                    {showQR ? 'Hide QR' : 'Show QR Code'}
                  </Button>
                </div>

                {showQR && (
                  <div className="flex flex-col items-center gap-4 p-4 rounded-lg bg-muted/50">
                    {isLoadingQR ? (
                      <Loader2 className="h-8 w-8 animate-spin" />
                    ) : qrData?.qr_code ? (
                      <>
                        <img
                          src={qrData.qr_code}
                          alt="QR Code"
                          className="w-48 h-48 rounded-lg border bg-white"
                        />
                        <p className="text-sm text-muted-foreground text-center">
                          Open WhatsApp on your phone, go to Settings → Linked Devices → Link a Device
                        </p>
                        <Button variant="outline" size="sm" onClick={() => refetchQR()}>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Refresh QR
                        </Button>
                      </>
                    ) : qrData?.status === 'connected' ? (
                      <div className="text-center py-4">
                        <Wifi className="h-12 w-12 mx-auto mb-2 text-green-500" />
                        <p className="font-medium">Connected!</p>
                      </div>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-muted-foreground mb-2">No QR code available</p>
                        <Button variant="outline" size="sm" onClick={() => refetchQR()}>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Retry
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="space-y-2">
              <span className="text-sm font-medium">Actions</span>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={() => restartMutation.mutate()}
                  disabled={restartMutation.isPending}
                >
                  {restartMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Restart Instance
                </Button>

                {isConnected && (
                  <Button
                    variant="outline"
                    className="text-red-600 hover:text-red-700"
                    onClick={() => logoutMutation.mutate()}
                    disabled={logoutMutation.isPending}
                  >
                    {logoutMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <LogOut className="h-4 w-4 mr-2" />
                    )}
                    Logout
                  </Button>
                )}
              </div>
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
