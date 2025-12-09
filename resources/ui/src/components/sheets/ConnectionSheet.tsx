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
  Bot,
  ExternalLink,
  Server,
  Play,
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
  channelType: 'whatsapp' | 'discord' | 'slack';
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConnectionSheet({ instanceName, channelType, open, onOpenChange }: ConnectionSheetProps) {
  const [showQR, setShowQR] = useState(false);
  const queryClient = useQueryClient();

  // Fetch instance details
  const { data: instance } = useQuery({
    queryKey: ['instance', instanceName],
    queryFn: () => api.instances.get(instanceName),
    enabled: open,
  });

  // Connection state query - use channel-aware API
  const { data: connectionState, isLoading: isLoadingState } = useQuery({
    queryKey: ['connection-state', instanceName],
    queryFn: () => api.instances.getStatus(instanceName),
    refetchInterval: open ? 5000 : false,
    enabled: open,
  });

  // QR code query (WhatsApp only)
  const { data: qrData, isLoading: isLoadingQR, refetch: refetchQR } = useQuery({
    queryKey: ['qr-code', instanceName],
    queryFn: () => api.instances.getQR(instanceName),
    enabled: open && showQR && channelType === 'whatsapp' && connectionState?.state !== 'open',
    refetchInterval: showQR && channelType === 'whatsapp' && connectionState?.state !== 'open' ? 5000 : false,
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

  // Start Evolution mutation (WhatsApp only)
  const startEvolutionMutation = useMutation({
    mutationFn: () => api.gateway.startChannel('evolution'),
    onSuccess: () => {
      toast.success('Starting WhatsApp service...');
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
        queryClient.invalidateQueries({ queryKey: ['qr-code', instanceName] });
      }, 2000);
    },
    onError: (error: Error) => {
      toast.error(`Failed to start WhatsApp service: ${error.message}`);
    },
  });

  // Determine connection state based on channel type
  const getConnectionState = () => {
    if (channelType === 'discord') {
      // Discord uses different status field
      const discordStatus = connectionState?.channel_data?.status || connectionState?.status;
      return discordStatus === 'connected' || discordStatus === 'ready' ? 'open' : 'disconnected';
    }
    // WhatsApp uses evolution status
    return connectionState?.state || instance?.evolution_status?.state || 'unknown';
  };

  const state = getConnectionState();
  const isConnected = state === 'open';
  const isConnecting = state === 'connecting';

  // Profile data varies by channel type
  const profile = channelType === 'discord'
    ? connectionState?.channel_data || {}
    : instance?.evolution_status || {};

  // Discord-specific data
  const discordData = channelType === 'discord' ? connectionState?.channel_data : null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            {channelType === 'discord' ? (
              <Bot className="h-5 w-5" />
            ) : (
              <Wifi className="h-5 w-5" />
            )}
            Connection - {instanceName}
          </SheetTitle>
          <SheetDescription>
            {channelType === 'discord'
              ? 'Manage Discord bot connection and status'
              : 'Manage WhatsApp connection and authentication'}
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

            {/* Profile - Channel-aware */}
            <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
              <Avatar className="h-16 w-16">
                {channelType === 'discord' ? (
                  <>
                    <AvatarImage src={discordData?.avatar_url || undefined} />
                    <AvatarFallback>
                      <Bot className="h-8 w-8" />
                    </AvatarFallback>
                  </>
                ) : (
                  <>
                    <AvatarImage src={profile.profile_picture_url || instance?.profile_pic_url || undefined} />
                    <AvatarFallback>
                      <User className="h-8 w-8" />
                    </AvatarFallback>
                  </>
                )}
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate text-lg">
                  {channelType === 'discord'
                    ? discordData?.bot_name || instanceName
                    : profile.profile_name || instance?.profile_name || instanceName}
                </p>
                <p className="text-sm text-muted-foreground truncate">
                  {channelType === 'discord'
                    ? discordData?.bot_id || 'Bot not connected'
                    : profile.owner_jid || instance?.owner_jid || 'No number connected'}
                </p>
              </div>
            </div>

            {/* WhatsApp QR Code Section */}
            {channelType === 'whatsapp' && !isConnected && (
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
                      <div className="text-center py-4 space-y-3">
                        <p className="text-muted-foreground">No QR code available</p>
                        <p className="text-sm text-muted-foreground">
                          The WhatsApp service may not be running.
                        </p>
                        <div className="flex flex-col gap-2">
                          <Button
                            onClick={() => startEvolutionMutation.mutate()}
                            disabled={startEvolutionMutation.isPending}
                          >
                            {startEvolutionMutation.isPending ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Starting...
                              </>
                            ) : (
                              <>
                                <Play className="h-4 w-4 mr-2" />
                                Start WhatsApp Service
                              </>
                            )}
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => refetchQR()}>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Retry QR Code
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Discord Bot Info Section */}
            {channelType === 'discord' && (
              <div className="space-y-4">
                <span className="text-sm font-medium">Bot Information</span>
                <div className="p-4 rounded-lg bg-muted/50 space-y-3">
                  {isConnected ? (
                    <>
                      {/* Connected Guilds */}
                      {discordData?.guilds && discordData.guilds.length > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-2">Connected Servers</p>
                          <div className="space-y-1">
                            {discordData.guilds.slice(0, 5).map((guild) => (
                              <div key={guild.id} className="flex items-center gap-2 text-sm">
                                <Server className="h-3 w-3 text-muted-foreground" />
                                <span className="truncate">{guild.name}</span>
                              </div>
                            ))}
                            {discordData.guilds.length > 5 && (
                              <p className="text-xs text-muted-foreground">
                                +{discordData.guilds.length - 5} more servers
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-4">
                      <Bot className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mb-3">Bot is not connected</p>
                      {discordData?.invite_url && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.open(discordData.invite_url, '_blank')}
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Add Bot to Server
                        </Button>
                      )}
                    </div>
                  )}
                </div>
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
