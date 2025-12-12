import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { DiscordConnector } from '@/components/instances/DiscordConnector';
import { DiscordInstallModal } from '@/components/DiscordInstallModal';
import { api } from '@/lib';
import type { InstanceConfig } from '@/lib';
import {
  ArrowLeft,
  Plus,
  Play,
  Square,
  RotateCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Settings,
  Trash2,
} from 'lucide-react';

// Discord icon as SVG
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
  </svg>
);

export default function DiscordService() {
  const queryClient = useQueryClient();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardInstanceName, setWizardInstanceName] = useState('');
  const [nameDialogOpen, setNameDialogOpen] = useState(false);
  const [newBotName, setNewBotName] = useState('');

  // Discord installation states
  const [showDiscordInstallModal, setShowDiscordInstallModal] = useState(false);
  const [checkingInstall, setCheckingInstall] = useState(false);
  const [installFlow, setInstallFlow] = useState<'addBot' | 'startService'>('addBot');

  // Check if discord.py is installed on page load
  const { data: discordInstallStatus, isLoading: installStatusLoading } = useQuery({
    queryKey: ['discord-installed'],
    queryFn: () => api.gateway.checkDiscordInstalled(),
    refetchInterval: 30000, // Re-check every 30 seconds
  });

  const discordInstalled = discordInstallStatus?.installed ?? null;

  // Fetch Discord instances
  const { data: instances, isLoading: instancesLoading } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_status: true }),
    refetchInterval: 10000,
  });

  // Fetch gateway channels status
  const { data: channelsData } = useQuery({
    queryKey: ['gateway-channels'],
    queryFn: () => api.gateway.getChannels(),
    refetchInterval: 5000,
  });

  const discordInstances = instances?.filter((i) => i.channel_type === 'discord') || [];
  const discordChannel = channelsData?.channels?.find((c) => c.name === 'discord');
  const isDiscordRunning = discordChannel?.running || false;
  const hasDiscordBots = discordInstances.length > 0;

  // Discord is only truly running if installed AND process running
  const isDiscordReady = discordInstalled === true && isDiscordRunning;

  // Start service mutation
  const startMutation = useMutation({
    mutationFn: () => api.gateway.startChannel('discord'),
    onSuccess: () => {
      toast.success('Discord service started');
      queryClient.invalidateQueries({ queryKey: ['gateway-channels'] });
    },
    onError: (err: Error) => {
      toast.error(`Failed to start service: ${err.message}`);
    },
  });

  // Stop service mutation
  const stopMutation = useMutation({
    mutationFn: () => api.gateway.stopChannel('discord'),
    onSuccess: () => {
      toast.success('Discord service stopped');
      queryClient.invalidateQueries({ queryKey: ['gateway-channels'] });
    },
    onError: (err: Error) => {
      toast.error(`Failed to stop service: ${err.message}`);
    },
  });

  // Restart service mutation
  const restartMutation = useMutation({
    mutationFn: () => api.gateway.restartChannel('discord'),
    onSuccess: () => {
      toast.success('Discord service restarted');
      queryClient.invalidateQueries({ queryKey: ['gateway-channels'] });
    },
    onError: (err: Error) => {
      toast.error(`Failed to restart service: ${err.message}`);
    },
  });

  // Delete instance mutation
  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.instances.delete(name),
    onSuccess: (_: void, name) => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Bot "${name}" deleted`);
    },
    onError: (err: Error, name) => {
      toast.error(`Failed to delete "${name}": ${err.message}`);
    },
  });

  const isServiceBusy = startMutation.isPending || stopMutation.isPending || restartMutation.isPending;

  const handleAddBot = async () => {
    // Check if Discord is installed first
    setInstallFlow('addBot');
    setCheckingInstall(true);
    try {
      const status = await api.gateway.checkDiscordInstalled();

      if (!status.installed) {
        // Show installation modal
        setShowDiscordInstallModal(true);
        return;
      }
    } catch (err) {
      console.error('Failed to check Discord installation:', err);
      // Assume not installed if check fails
      setShowDiscordInstallModal(true);
      return;
    } finally {
      setCheckingInstall(false);
    }

    // Generate a default bot name
    const baseName = 'discord-bot';
    const existingNames = discordInstances.map((i) => i.name);
    let counter = 1;
    let newName = baseName;
    while (existingNames.includes(newName)) {
      newName = `${baseName}-${counter}`;
      counter++;
    }
    setNewBotName(newName);
    setNameDialogOpen(true);
  };

  const handleStartService = async () => {
    // Check if Discord is installed first
    setInstallFlow('startService');
    setCheckingInstall(true);
    try {
      const status = await api.gateway.checkDiscordInstalled();

      if (!status.installed) {
        // Show installation modal, then start service after success
        setShowDiscordInstallModal(true);
        return;
      }
    } catch (err) {
      console.error('Failed to check Discord installation:', err);
      setShowDiscordInstallModal(true);
      return;
    } finally {
      setCheckingInstall(false);
    }

    // Discord installed, start service
    startMutation.mutate();
  };

  // Continue after Discord is installed - handle both flows
  const handleInstallSuccess = () => {
    // Refetch installation status
    queryClient.invalidateQueries({ queryKey: ['discord-installed'] });
    setShowDiscordInstallModal(false);

    if (installFlow === 'startService') {
      // Start the service now that discord.py is installed
      startMutation.mutate();
    } else {
      // Proceed to add bot
      const baseName = 'discord-bot';
      const existingNames = discordInstances.map((i) => i.name);
      let counter = 1;
      let newName = baseName;
      while (existingNames.includes(newName)) {
        newName = `${baseName}-${counter}`;
        counter++;
      }
      setNewBotName(newName);
      setNameDialogOpen(true);
    }
  };

  const handleNameConfirm = () => {
    if (newBotName.trim()) {
      setWizardInstanceName(newBotName.trim().toLowerCase().replace(/\s+/g, '-'));
      setNameDialogOpen(false);
      setWizardOpen(true);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Discord Service"
          subtitle="Manage your Discord bot connections"
          actions={
            <Button variant="outline" asChild>
              <Link to="/services">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Services
              </Link>
            </Button>
          }
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in">
            {/* Service Status Card */}
            <Card className="border-border elevation-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-[#5865F2] flex items-center justify-center">
                      <DiscordIcon className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <CardTitle>Discord Bot Service</CardTitle>
                      <CardDescription>Manage Discord bot integrations</CardDescription>
                    </div>
                  </div>
                  {installStatusLoading ? (
                    <Skeleton className="h-6 w-20" />
                  ) : discordInstalled === false ? (
                    <Badge className="bg-orange-500/10 text-orange-500 border-orange-500/20">
                      <AlertCircle className="h-3 w-3 mr-1" />
                      Not Installed
                    </Badge>
                  ) : !hasDiscordBots ? (
                    <Badge variant="secondary">
                      <AlertCircle className="h-3 w-3 mr-1" />
                      Not Configured
                    </Badge>
                  ) : isDiscordReady ? (
                    <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Running
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="bg-red-500/10 text-red-500 border-red-500/20">
                      <XCircle className="h-3 w-3 mr-1" />
                      Stopped
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {discordInstalled === false ? (
                  <div className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      Discord.py is not installed. Install it to enable Discord bot functionality.
                    </p>
                    <Button
                      onClick={() => {
                        setInstallFlow('startService');
                        setShowDiscordInstallModal(true);
                      }}
                      disabled={checkingInstall}
                      className="bg-[#5865F2] hover:bg-[#4752C4]"
                    >
                      {checkingInstall ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Plus className="h-4 w-4 mr-2" />
                      )}
                      Install Discord
                    </Button>
                  </div>
                ) : hasDiscordBots ? (
                  <div className="flex items-center gap-3">
                    {!isDiscordReady ? (
                      <Button
                        onClick={handleStartService}
                        disabled={isServiceBusy || checkingInstall}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        {startMutation.isPending || checkingInstall ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Play className="h-4 w-4 mr-2" />
                        )}
                        Start Service
                      </Button>
                    ) : (
                      <>
                        <Button variant="destructive" onClick={() => stopMutation.mutate()} disabled={isServiceBusy}>
                          {stopMutation.isPending ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Square className="h-4 w-4 mr-2" />
                          )}
                          Stop
                        </Button>
                        <Button variant="outline" onClick={() => restartMutation.mutate()} disabled={isServiceBusy}>
                          {restartMutation.isPending ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <RotateCw className="h-4 w-4 mr-2" />
                          )}
                          Restart
                        </Button>
                      </>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Add a Discord bot to enable the service.</p>
                )}
              </CardContent>
            </Card>

            {/* Bots Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Discord Bots</h2>
                <Button onClick={handleAddBot} disabled={checkingInstall}>
                  {checkingInstall ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  Add Bot
                </Button>
              </div>

              {instancesLoading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {[1, 2, 3].map((i) => (
                    <Card key={i} className="border-border">
                      <CardHeader>
                        <Skeleton className="h-5 w-32 mb-2" />
                        <Skeleton className="h-4 w-24" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-8 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : discordInstances.length === 0 ? (
                <Card className="border-border border-dashed">
                  <CardContent className="py-12 text-center">
                    <div className="flex flex-col items-center space-y-4">
                      <div className="h-16 w-16 rounded-2xl bg-muted flex items-center justify-center">
                        <DiscordIcon className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-medium text-foreground">No Discord bots configured</p>
                        <p className="text-sm text-muted-foreground mt-1">Add a Discord bot to get started</p>
                      </div>
                      <Button onClick={handleAddBot} disabled={checkingInstall}>
                        {checkingInstall ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Plus className="h-4 w-4 mr-2" />
                        )}
                        Add Bot
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {discordInstances.map((instance) => (
                    <BotCard
                      key={instance.id}
                      instance={instance}
                      onDelete={() => deleteMutation.mutate(instance.name)}
                      isDeleting={deleteMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Name Input Dialog */}
      <Dialog open={nameDialogOpen} onOpenChange={setNameDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Name Your Bot</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="bot-name">Bot Name</Label>
              <Input
                id="bot-name"
                value={newBotName}
                onChange={(e) => setNewBotName(e.target.value)}
                placeholder="e.g. my-discord-bot"
                onKeyDown={(e) => e.key === 'Enter' && handleNameConfirm()}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">A friendly name to identify this bot connection</p>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setNameDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleNameConfirm} disabled={!newBotName.trim()}>
                Continue
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Bot Dialog (Token Input) */}
      <Dialog open={wizardOpen} onOpenChange={setWizardOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Connect Discord Bot</DialogTitle>
          </DialogHeader>
          <DiscordConnector
            instanceName={wizardInstanceName}
            onBack={() => setWizardOpen(false)}
            onSuccess={() => {
              setWizardOpen(false);
              queryClient.invalidateQueries({ queryKey: ['instances'] });
              // Start Discord service after adding first bot
              if (discordInstances.length === 0) {
                startMutation.mutate();
              }
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Discord Install Modal */}
      <DiscordInstallModal
        open={showDiscordInstallModal}
        onOpenChange={(open) => {
          setShowDiscordInstallModal(open);
        }}
        onSuccess={handleInstallSuccess}
        onRetry={() => {
          // Modal handles retry internally
        }}
      />
    </DashboardLayout>
  );
}

// Bot card component
function BotCard({
  instance,
  onDelete,
  isDeleting,
}: {
  instance: InstanceConfig;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const hasToken = instance.has_discord_bot_token || !!instance.discord_bot_token;

  return (
    <Card className="border-border hover:elevation-md transition-all">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{instance.name}</CardTitle>
          {hasToken ? (
            <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Configured
            </Badge>
          ) : (
            <Badge variant="secondary">
              <AlertCircle className="h-3 w-3 mr-1" />
              No Token
            </Badge>
          )}
        </div>
        {instance.discord_client_id && (
          <CardDescription className="font-mono text-xs">ID: {instance.discord_client_id}</CardDescription>
        )}
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild className="flex-1">
            <Link to="/instances">
              <Settings className="h-4 w-4 mr-1" />
              Settings
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onDelete}
            disabled={isDeleting}
            className="text-destructive hover:text-destructive"
          >
            {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
