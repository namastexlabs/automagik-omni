import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api, HealthResponse, setInstanceKey, cn } from '@/lib';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Phone,
  MessageSquare,
  Users,
  MessagesSquare,
  Settings,
  RefreshCw,
  LogOut,
  QrCode,
  Smartphone,
  Clock,
  Shield,
  Bell,
  BellOff,
  Eye,
  EyeOff,
  Copy,
  PhoneOff,
  History,
  Loader2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Wifi,
  WifiOff,
} from 'lucide-react';

// Evolution instance detail from health endpoint
interface EvolutionInstanceDetail {
  name: string;
  connectionStatus: string;
  profileName?: string;
  profilePicUrl?: string;
  ownerJid?: string;
  integration?: string;
  createdAt?: string;
  updatedAt?: string;
  counts: {
    messages: number;
    contacts: number;
    chats: number;
  };
  settings?: {
    rejectCall?: boolean;
    groupsIgnore?: boolean;
    alwaysOnline?: boolean;
    readMessages?: boolean;
    readStatus?: boolean;
    syncFullHistory?: boolean;
  };
  integrations?: {
    chatwoot?: boolean;
    rabbitmq?: boolean;
    websocket?: boolean;
  };
}

function formatPhone(jid?: string): string | null {
  if (!jid) return null;
  const phone = jid.split('@')[0];
  if (phone.length >= 12) {
    return `+${phone.slice(0, 2)} ${phone.slice(2, 4)} ${phone.slice(4, 9)}-${phone.slice(9)}`;
  }
  return `+${phone}`;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface InstanceManageCardProps {
  instance: EvolutionInstanceDetail;
  onRestart: (name: string) => void;
  onLogout: (name: string) => void;
  isRestarting: boolean;
  isLoggingOut: boolean;
}

function InstanceManageCard({
  instance,
  onRestart,
  onLogout,
  isRestarting,
  isLoggingOut,
}: InstanceManageCardProps) {
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const isConnected = instance.connectionStatus === 'open';

  return (
    <Card className="overflow-hidden">
      {/* Header with profile */}
      <CardHeader className="pb-4">
        <div className="flex items-start gap-4">
          <Avatar className="h-16 w-16 border-2 border-border">
            {instance.profilePicUrl ? (
              <AvatarImage src={instance.profilePicUrl} alt={instance.profileName || instance.name} />
            ) : null}
            <AvatarFallback className="bg-primary/10 text-primary text-xl">
              {(instance.profileName || instance.name).slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <CardTitle className="text-xl truncate">
                {instance.profileName || instance.name}
              </CardTitle>
              <Badge
                variant={isConnected ? 'default' : 'destructive'}
                className={cn(
                  'flex items-center gap-1',
                  isConnected ? 'bg-success text-success-foreground' : ''
                )}
              >
                {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                {isConnected ? 'Connected' : instance.connectionStatus}
              </Badge>
            </div>

            {instance.ownerJid && (
              <CardDescription className="flex items-center gap-1">
                <Phone className="h-3.5 w-3.5" />
                {formatPhone(instance.ownerJid)}
              </CardDescription>
            )}

            <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
              <Smartphone className="h-3 w-3" />
              <span>{instance.integration || 'WhatsApp'}</span>
              <span className="text-muted-foreground/50">•</span>
              <span>Instance: {instance.name}</span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Statistics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <MessageSquare className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-bold">{instance.counts.messages.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">Messages</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Users className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-bold">{instance.counts.contacts}</div>
            <div className="text-xs text-muted-foreground">Contacts</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <MessagesSquare className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-bold">{instance.counts.chats}</div>
            <div className="text-xs text-muted-foreground">Chats</div>
          </div>
        </div>

        <Separator />

        {/* Settings Section */}
        {instance.settings && (
          <div className="space-y-4">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Instance Settings
            </h4>

            <div className="grid gap-3">
              <SettingRow
                icon={instance.settings.readMessages ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                label="Auto-read messages"
                description="Automatically mark messages as read"
                enabled={instance.settings.readMessages}
              />
              <SettingRow
                icon={instance.settings.alwaysOnline ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                label="Always online"
                description="Show as online even when inactive"
                enabled={instance.settings.alwaysOnline}
              />
              <SettingRow
                icon={instance.settings.rejectCall ? <PhoneOff className="h-4 w-4" /> : <Phone className="h-4 w-4" />}
                label="Reject calls"
                description="Automatically reject incoming calls"
                enabled={instance.settings.rejectCall}
              />
              <SettingRow
                icon={instance.settings.groupsIgnore ? <BellOff className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
                label="Ignore groups"
                description="Don't process group messages"
                enabled={instance.settings.groupsIgnore}
              />
              <SettingRow
                icon={<History className="h-4 w-4" />}
                label="Full history sync"
                description="Sync complete message history"
                enabled={instance.settings.syncFullHistory}
              />
            </div>
          </div>
        )}

        <Separator />

        {/* Timestamps */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              Created
            </span>
            <span className="font-medium">{formatDate(instance.createdAt)}</span>
          </div>
          <div>
            <span className="text-muted-foreground flex items-center gap-1">
              <RefreshCw className="h-3.5 w-3.5" />
              Last updated
            </span>
            <span className="font-medium">{formatDate(instance.updatedAt)}</span>
          </div>
        </div>

        <Separator />

        {/* Evolution API Credentials */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">Evolution API Key</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowApiKey(!showApiKey)}
              className="h-6 px-2"
            >
              {showApiKey ? (
                <EyeOff className="h-3 w-3" />
              ) : (
                <Eye className="h-3 w-3" />
              )}
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <code className="flex-1 px-2 py-1 text-xs bg-muted rounded font-mono">
              {showApiKey
                ? instance.evolution_key || '••••••••••••••••••••••••••••••••'
                : '••••••••••••••••••••••••••••••••'}
            </code>
            {showApiKey && instance.evolution_key && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(instance.evolution_key);
                  toast.success('API key copied to clipboard');
                }}
                className="h-6 px-2"
              >
                <Copy className="h-3 w-3" />
              </Button>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            Auto-generated key for Evolution API authentication
          </p>
        </div>

        <Separator />

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => onRestart(instance.name)}
            disabled={isRestarting}
          >
            {isRestarting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Restart
          </Button>
          <Button
            variant="outline"
            className="flex-1 hover:bg-destructive/10 hover:text-destructive hover:border-destructive"
            onClick={() => setShowLogoutDialog(true)}
            disabled={isLoggingOut || !isConnected}
          >
            {isLoggingOut ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <LogOut className="h-4 w-4 mr-2" />
            )}
            Logout
          </Button>
        </div>
      </CardContent>

      {/* Logout Confirmation Dialog */}
      <AlertDialog open={showLogoutDialog} onOpenChange={setShowLogoutDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-warning" />
              Logout from WhatsApp
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to logout <span className="font-semibold text-foreground">"{instance.profileName || instance.name}"</span>?
              <br /><br />
              This will disconnect the WhatsApp session. You'll need to scan a QR code to reconnect.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                onLogout(instance.name);
                setShowLogoutDialog(false);
              }}
              className="bg-warning text-warning-foreground hover:bg-warning/90"
            >
              Logout
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}

function SettingRow({
  icon,
  label,
  description,
  enabled,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  enabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
      <div className="flex items-center gap-3">
        <div className={cn(
          'p-2 rounded-md',
          enabled ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'
        )}>
          {icon}
        </div>
        <div>
          <div className="font-medium text-sm">{label}</div>
          <div className="text-xs text-muted-foreground">{description}</div>
        </div>
      </div>
      <Badge variant={enabled ? 'default' : 'outline'} className={cn(
        enabled ? 'bg-success/10 text-success border-success/20' : ''
      )}>
        {enabled ? 'Enabled' : 'Disabled'}
      </Badge>
    </div>
  );
}

export function ManageTab() {
  const queryClient = useQueryClient();

  const { data: health, isLoading } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 10000,
  });

  const restartMutation = useMutation({
    mutationFn: (name: string) => api.evolution.restart(name),
    onSuccess: (_, name) => {
      toast.success(`Instance "${name}" restarted successfully`);
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (error: Error, name) => {
      toast.error(`Failed to restart "${name}": ${error.message}`);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: (name: string) => api.evolution.logout(name),
    onSuccess: (_, name) => {
      toast.success(`Logged out from "${name}"`);
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (error: Error, name) => {
      toast.error(`Failed to logout "${name}": ${error.message}`);
    },
  });

  const discoverMutation = useMutation({
    mutationFn: () => api.instances.discover(),
    onSuccess: (data) => {
      toast.success(
        `Resync complete - ${data.total} instance${data.total !== 1 ? 's' : ''} configured`
      );
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (error: Error) => {
      toast.error(`Resync failed: ${error.message}`);
    },
  });

  // Extract Evolution instance details from health
  const evolutionDetails = health?.services?.evolution?.details as {
    instances?: { total: number; connected: number; disconnected: number };
    totals?: { messages: number; contacts: number; chats: number };
    instanceDetails?: EvolutionInstanceDetail[];
    version?: string;
    whatsappWebVersion?: string;
  } | undefined;

  const instances = evolutionDetails?.instanceDetails || [];

  // Populate per-instance authentication keys when instances are loaded
  useEffect(() => {
    instances.forEach(instance => {
      if (instance.name && instance.evolution_key) {
        setInstanceKey(instance.name, instance.evolution_key);
      }
    });
  }, [instances]);

  return (
    <div className="space-y-6">
      {/* Evolution API Status Header */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="h-5 w-5" />
                WhatsApp Web Management
              </CardTitle>
              <CardDescription>
                Manage your WhatsApp instances, view settings, and monitor connections
              </CardDescription>
            </div>
            <div className="flex items-center gap-4">
              {evolutionDetails && (
                <div className="flex items-center gap-4 text-sm">
                  <div className="text-right">
                    <div className="text-muted-foreground">WhatsApp Web API</div>
                    <div className="font-medium">v{evolutionDetails.version || 'Unknown'}</div>
                  </div>
                  <Separator orientation="vertical" className="h-8" />
                  <div className="text-right">
                    <div className="text-muted-foreground">WhatsApp Web</div>
                    <div className="font-medium">{evolutionDetails.whatsappWebVersion || 'Unknown'}</div>
                  </div>
                </div>
              )}
              {evolutionDetails && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => discoverMutation.mutate()}
                  disabled={discoverMutation.isPending}
                  className="whitespace-nowrap"
                >
                  {discoverMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Resync Instances
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        {evolutionDetails?.instances && (
          <CardContent className="pt-0">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-success" />
                <span className="text-sm">
                  {evolutionDetails.instances.connected} connected
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-destructive" />
                <span className="text-sm">
                  {evolutionDetails.instances.disconnected} disconnected
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-muted-foreground" />
                <span className="text-sm">
                  {evolutionDetails.instances.total} total
                </span>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Instance Cards */}
      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-[500px]" />
          <Skeleton className="h-[500px]" />
        </div>
      ) : instances.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {instances.map((instance) => (
            <InstanceManageCard
              key={instance.name}
              instance={instance}
              onRestart={(name) => restartMutation.mutate(name)}
              onLogout={(name) => logoutMutation.mutate(name)}
              isRestarting={restartMutation.isPending && restartMutation.variables === instance.name}
              isLoggingOut={logoutMutation.isPending && logoutMutation.variables === instance.name}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Smartphone className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h3 className="text-lg font-medium mb-2">No WhatsApp Instances</h3>
            <p className="text-muted-foreground">
              No WhatsApp instances found. Make sure the WhatsApp Web API is running and configured.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
