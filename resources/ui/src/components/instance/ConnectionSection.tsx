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
  MessageSquare,
  Users,
  Bot,
  ExternalLink,
  Server,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { api } from '@/lib';
import type { InstanceConfig } from '@/lib';

interface ConnectionSectionProps {
  instanceName: string;
  instance: InstanceConfig;
}

export function ConnectionSection({ instanceName, instance }: ConnectionSectionProps) {
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const channelType = instance.channel_type || 'whatsapp';

  // Connection state query - use channel-aware API
  const { data: connectionState, isLoading: isLoadingState } = useQuery({
    queryKey: ['connection-state', instanceName],
    queryFn: () => api.instances.getStatus(instanceName),
    refetchInterval: 5000,
  });

  // QR code query (WhatsApp only, when dialog is open and not connected)
  const { data: qrData, isLoading: isLoadingQR, refetch: refetchQR } = useQuery({
    queryKey: ['qr-code', instanceName],
    queryFn: () => api.instances.getQR(instanceName),
    enabled: qrDialogOpen && channelType === 'whatsapp' && connectionState?.state !== 'open',
    refetchInterval: qrDialogOpen && channelType === 'whatsapp' && connectionState?.state !== 'open' ? 5000 : false,
  });

  // Restart mutation - use channel-aware API
  const restartMutation = useMutation({
    mutationFn: () => api.instances.restart(instanceName),
    onSuccess: () => {
      toast.success('Instance restarted');
      queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to restart: ${error.message}`);
    },
  });

  // Logout mutation - use channel-aware API
  const logoutMutation = useMutation({
    mutationFn: () => api.instances.logout(instanceName),
    onSuccess: () => {
      toast.success('Logged out');
      queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to logout: ${error.message}`);
    },
  });

  // Determine connection state based on channel type
  const getConnectionState = () => {
    if (channelType === 'discord') {
      const discordStatus = connectionState?.channel_data?.status || connectionState?.status;
      return discordStatus === 'connected' || discordStatus === 'ready' ? 'open' : 'disconnected';
    }
    return connectionState?.state || instance.evolution_status?.state || 'unknown';
  };

  const state = getConnectionState();
  const isConnected = state === 'open';
  const isConnecting = state === 'connecting';

  // Profile data varies by channel type
  const profile = channelType === 'discord'
    ? connectionState?.channel_data || {}
    : instance.evolution_status || {};

  // Discord-specific data
  const discordData = channelType === 'discord' ? connectionState?.channel_data : null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          Connection
          <Badge
            variant={isConnected ? 'default' : 'secondary'}
            className={isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500' : 'bg-red-500'}
          >
            {isConnected ? (
              <><Wifi className="h-3 w-3 mr-1" /> Connected</>
            ) : isConnecting ? (
              <><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Connecting</>
            ) : (
              <><WifiOff className="h-3 w-3 mr-1" /> Disconnected</>
            )}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Profile - Channel-aware */}
        <div className="flex items-center gap-3">
          <Avatar className="h-12 w-12">
            {channelType === 'discord' ? (
              <>
                <AvatarImage src={discordData?.avatar_url || undefined} />
                <AvatarFallback>
                  <Bot className="h-6 w-6" />
                </AvatarFallback>
              </>
            ) : (
              <>
                <AvatarImage src={profile.profile_picture_url || instance.profile_pic_url || undefined} />
                <AvatarFallback>
                  <User className="h-6 w-6" />
                </AvatarFallback>
              </>
            )}
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">
              {channelType === 'discord'
                ? discordData?.bot_name || instanceName
                : profile.profile_name || instance.profile_name || instanceName}
            </p>
            <p className="text-sm text-muted-foreground truncate">
              {channelType === 'discord'
                ? discordData?.bot_id || 'Bot not connected'
                : profile.owner_jid || instance.owner_jid || 'No number connected'}
            </p>
          </div>
        </div>

        {/* WhatsApp Stats */}
        {channelType === 'whatsapp' && isConnected && (
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded-md bg-muted/50">
              <Users className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Contacts</p>
              <p className="font-medium text-sm">-</p>
            </div>
            <div className="p-2 rounded-md bg-muted/50">
              <MessageSquare className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Chats</p>
              <p className="font-medium text-sm">-</p>
            </div>
            <div className="p-2 rounded-md bg-muted/50">
              <MessageSquare className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Messages</p>
              <p className="font-medium text-sm">-</p>
            </div>
          </div>
        )}

        {/* Discord Stats */}
        {channelType === 'discord' && isConnected && discordData?.guilds && (
          <div className="p-2 rounded-md bg-muted/50">
            <div className="flex items-center gap-2 text-sm">
              <Server className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Servers:</span>
              <span className="font-medium">{discordData.guilds.length}</span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {/* WhatsApp QR Code Button */}
          {channelType === 'whatsapp' && !isConnected && (
            <Dialog open={qrDialogOpen} onOpenChange={setQrDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="flex-1">
                  <QrCode className="h-4 w-4 mr-2" />
                  Scan QR
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Scan QR Code</DialogTitle>
                </DialogHeader>
                <div className="flex flex-col items-center gap-4 py-4">
                  {isLoadingQR ? (
                    <Loader2 className="h-8 w-8 animate-spin" />
                  ) : qrData?.qr_code ? (
                    <>
                      <img
                        src={qrData.qr_code}
                        alt="QR Code"
                        className="w-64 h-64 rounded-lg border"
                      />
                      <p className="text-sm text-muted-foreground text-center">
                        Open WhatsApp on your phone, go to Settings &gt; Linked Devices &gt; Link a Device
                      </p>
                      <Button variant="outline" onClick={() => refetchQR()}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Refresh QR
                      </Button>
                    </>
                  ) : qrData?.status === 'connected' || connectionState?.state === 'open' ? (
                    <div className="text-center">
                      <Wifi className="h-12 w-12 mx-auto mb-2 text-green-500" />
                      <p className="font-medium">Connected!</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <p className="text-muted-foreground">No QR code available</p>
                      <Button variant="outline" className="mt-2" onClick={() => refetchQR()}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Retry
                      </Button>
                    </div>
                  )}
                </div>
              </DialogContent>
            </Dialog>
          )}

          {/* Discord Add to Server Button */}
          {channelType === 'discord' && !isConnected && discordData?.invite_url && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => window.open(discordData.invite_url, '_blank')}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Add to Server
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => restartMutation.mutate()}
            disabled={restartMutation.isPending}
          >
            {restartMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Restart
          </Button>

          {isConnected && (
            <Button
              variant="outline"
              size="sm"
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
      </CardContent>
    </Card>
  );
}
