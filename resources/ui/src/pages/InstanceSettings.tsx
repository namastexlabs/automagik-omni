import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { api } from '@/lib';
import type { InstanceConfig, InstanceUpdateRequest, AgentProvider } from '@/lib';
import {
  Wifi,
  WifiOff,
  Bot,
  MessageSquare,
  Webhook,
  Save,
  Loader2,
  RefreshCw,
  LogOut,
  QrCode,
  ArrowLeft,
  Clock,
  SplitSquareVertical,
  User,
  AlertCircle,
  Settings,
  Phone,
  Eye,
  Users,
  History,
} from 'lucide-react';
import { WhatsAppIcon, DiscordIcon } from '@/components/icons/BrandIcons';

export default function InstanceSettings() {
  const { instanceName } = useParams<{ instanceName: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('connection');
  const [hasChanges, setHasChanges] = useState(false);
  const [showQR, setShowQR] = useState(false);

  // Form state for editable fields
  const [agentForm, setAgentForm] = useState({
    agent_api_url: '',
    agent_api_key: '',
    agent_id: '',
    agent_type: 'agent',
    agent_timeout: 60,
    agent_stream_mode: false,
    agent_provider_id: null as number | null,
  });

  const [messagesForm, setMessagesForm] = useState({
    enable_auto_split: true,
    message_debounce_seconds: 0,
    message_debounce_mode: 'disabled' as 'disabled' | 'fixed' | 'randomized',
    message_debounce_min_ms: 0,
    message_debounce_max_ms: 0,
    message_split_delay_mode: 'randomized' as 'disabled' | 'fixed' | 'randomized',
    message_split_delay_fixed_ms: 0,
    message_split_delay_min_ms: 300,
    message_split_delay_max_ms: 1000,
    disable_username_prefix: false,
  });

  // Behavior form (WhatsApp Evolution settings)
  const [behaviorForm, setBehaviorForm] = useState({
    rejectCall: false,
    msgCall: '',
    groupsIgnore: false,
    alwaysOnline: false,
    readMessages: false,
    readStatus: false,
    syncFullHistory: false,
  });
  const [behaviorHasChanges, setBehaviorHasChanges] = useState(false);

  // Fetch instance
  const { data: instance, isLoading: instanceLoading } = useQuery<InstanceConfig>({
    queryKey: ['instance', instanceName],
    queryFn: () => api.instances.get(instanceName!),
    enabled: !!instanceName,
  });

  // Fetch connection status
  const { data: connectionState, isLoading: statusLoading } = useQuery({
    queryKey: ['connection-state', instanceName],
    queryFn: () => api.instances.getStatus(instanceName!),
    refetchInterval: 5000,
    enabled: !!instanceName,
  });

  // Fetch providers for dropdown
  const { data: providers } = useQuery<AgentProvider[]>({
    queryKey: ['providers'],
    queryFn: () => api.providers.list(),
  });

  // Fetch QR code (WhatsApp only)
  const { data: qrData, isLoading: qrLoading } = useQuery({
    queryKey: ['qr-code', instanceName],
    queryFn: () => api.instances.getQR(instanceName!),
    enabled: showQR && instance?.channel_type === 'whatsapp' && connectionState?.status !== 'connected',
    refetchInterval: showQR ? 5000 : false,
  });

  // Fetch Evolution settings (WhatsApp only)
  const { data: evolutionSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ['evolution-settings', instanceName],
    queryFn: () => api.whatsappWeb.getSettings(instanceName!),
    enabled: !!instanceName && instance?.channel_type === 'whatsapp',
  });

  // Initialize form when instance loads
  useEffect(() => {
    if (instance) {
      setAgentForm({
        agent_api_url: instance.agent_api_url || '',
        agent_api_key: '',
        agent_id: instance.agent_id || '',
        agent_type: instance.agent_type || 'agent',
        agent_timeout: instance.agent_timeout || 60,
        agent_stream_mode: instance.agent_stream_mode || false,
        agent_provider_id: instance.agent_provider_id || null,
      });
      setMessagesForm({
        enable_auto_split: instance.enable_auto_split ?? true,
        message_debounce_seconds: instance.message_debounce_seconds ?? 0,
        message_debounce_mode: instance.message_debounce_mode ?? 'disabled',
        message_debounce_min_ms: instance.message_debounce_min_ms ?? 0,
        message_debounce_max_ms: instance.message_debounce_max_ms ?? 0,
        message_split_delay_mode: instance.message_split_delay_mode ?? 'randomized',
        message_split_delay_fixed_ms: instance.message_split_delay_fixed_ms ?? 0,
        message_split_delay_min_ms: instance.message_split_delay_min_ms ?? 300,
        message_split_delay_max_ms: instance.message_split_delay_max_ms ?? 1000,
        disable_username_prefix: instance.disable_username_prefix ?? false,
      });
      setHasChanges(false);
    }
  }, [instance]);

  // Initialize behavior form when Evolution settings load
  useEffect(() => {
    if (evolutionSettings) {
      setBehaviorForm({
        rejectCall: evolutionSettings.rejectCall ?? false,
        msgCall: evolutionSettings.msgCall ?? '',
        groupsIgnore: evolutionSettings.groupsIgnore ?? false,
        alwaysOnline: evolutionSettings.alwaysOnline ?? false,
        readMessages: evolutionSettings.readMessages ?? false,
        readStatus: evolutionSettings.readStatus ?? false,
        syncFullHistory: evolutionSettings.syncFullHistory ?? false,
      });
      setBehaviorHasChanges(false);
    }
  }, [evolutionSettings]);

  // Mutations
  const saveMutation = useMutation({
    mutationFn: (data: InstanceUpdateRequest) => api.instances.update(instanceName!, data),
    onSuccess: () => {
      toast.success('Settings saved');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['instance', instanceName] });
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to save settings');
    },
  });

  const restartMutation = useMutation({
    mutationFn: () => api.instances.restart(instanceName!),
    onSuccess: () => {
      toast.success('Instance restarted');
      queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const logoutMutation = useMutation({
    mutationFn: () => api.instances.logout(instanceName!),
    onSuccess: () => {
      toast.success('Logged out');
      queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const saveBehaviorMutation = useMutation({
    mutationFn: (data: typeof behaviorForm) => api.whatsappWeb.setSettings(instanceName!, data),
    onSuccess: () => {
      toast.success('Behavior settings saved');
      setBehaviorHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['evolution-settings', instanceName] });
    },
    onError: (err: Error) => toast.error(err.message || 'Failed to save behavior settings'),
  });

  // Helpers
  const updateAgentForm = <K extends keyof typeof agentForm>(key: K, value: (typeof agentForm)[K]) => {
    setAgentForm((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const updateMessagesForm = <K extends keyof typeof messagesForm>(key: K, value: (typeof messagesForm)[K]) => {
    setMessagesForm((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const updateBehaviorForm = <K extends keyof typeof behaviorForm>(key: K, value: (typeof behaviorForm)[K]) => {
    setBehaviorForm((prev) => ({ ...prev, [key]: value }));
    setBehaviorHasChanges(true);
  };

  const handleSave = () => {
    const updateData: InstanceUpdateRequest = {
      // Agent config
      agent_timeout: agentForm.agent_timeout,
      agent_stream_mode: agentForm.agent_stream_mode,
      agent_type: agentForm.agent_type,
      agent_provider_id: agentForm.agent_provider_id,
      // Messages config
      enable_auto_split: messagesForm.enable_auto_split,
      message_debounce_seconds: messagesForm.message_debounce_seconds,
      message_debounce_mode: messagesForm.message_debounce_mode,
      message_debounce_min_ms: messagesForm.message_debounce_min_ms,
      message_debounce_max_ms: messagesForm.message_debounce_max_ms,
      message_split_delay_mode: messagesForm.message_split_delay_mode,
      message_split_delay_fixed_ms: messagesForm.message_split_delay_fixed_ms,
      message_split_delay_min_ms: messagesForm.message_split_delay_min_ms,
      message_split_delay_max_ms: messagesForm.message_split_delay_max_ms,
      disable_username_prefix: messagesForm.disable_username_prefix,
    };

    if (agentForm.agent_api_url.trim()) updateData.agent_api_url = agentForm.agent_api_url.trim();
    if (agentForm.agent_api_key.trim()) updateData.agent_api_key = agentForm.agent_api_key.trim();
    if (agentForm.agent_id.trim()) updateData.agent_id = agentForm.agent_id.trim();

    saveMutation.mutate(updateData);
  };

  // Connection status
  const getConnectionStatus = () => {
    if (!connectionState) return { status: 'unknown', color: 'bg-gray-500' };
    const status = connectionState.status?.toLowerCase();
    if (status === 'connected' || status === 'open') return { status: 'Connected', color: 'bg-green-500' };
    if (status === 'connecting') return { status: 'Connecting', color: 'bg-yellow-500' };
    return { status: 'Disconnected', color: 'bg-red-500' };
  };

  const connStatus = getConnectionStatus();
  const isConnected = connStatus.status === 'Connected';

  if (!instanceName) {
    return (
      <DashboardLayout>
        <div className="p-8">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Instance name is required</AlertDescription>
          </Alert>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        {/* Header */}
        <PageHeader
          title={
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={() => navigate('/instances')}>
                <ArrowLeft className="h-5 w-5" />
              </Button>
              {instance?.channel_type === 'discord' ? (
                <DiscordIcon className="h-6 w-6 text-[#5865F2]" />
              ) : (
                <WhatsAppIcon className="h-6 w-6 text-[#25D366]" />
              )}
              <span>{instanceName}</span>
              <Badge className={connStatus.color}>{connStatus.status}</Badge>
            </div>
          }
          subtitle="Configure instance settings"
          actions={
            hasChanges ? (
              <Button onClick={handleSave} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                Save Changes
              </Button>
            ) : null
          }
        />

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {instanceLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          ) : (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <TabsList className={`grid w-full ${instance?.channel_type === 'whatsapp' ? 'grid-cols-5 max-w-3xl' : 'grid-cols-3 max-w-xl'}`}>
                <TabsTrigger value="connection" className="flex items-center gap-2">
                  <Wifi className="h-4 w-4" />
                  Connection
                </TabsTrigger>
                <TabsTrigger value="agent" className="flex items-center gap-2">
                  <Bot className="h-4 w-4" />
                  Agent
                </TabsTrigger>
                <TabsTrigger value="messages" className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Messages
                </TabsTrigger>
                {instance?.channel_type === 'whatsapp' && (
                  <TabsTrigger value="behavior" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Behavior
                  </TabsTrigger>
                )}
                {instance?.channel_type === 'whatsapp' && (
                  <TabsTrigger value="webhooks" className="flex items-center gap-2">
                    <Webhook className="h-4 w-4" />
                    Webhooks
                  </TabsTrigger>
                )}
              </TabsList>

              {/* Connection Tab */}
              <TabsContent value="connection" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      {isConnected ? <Wifi className="h-5 w-5 text-green-500" /> : <WifiOff className="h-5 w-5 text-red-500" />}
                      Connection Status
                    </CardTitle>
                    <CardDescription>
                      {instance?.channel_type === 'discord' ? 'Discord bot connection status' : 'WhatsApp Web connection status'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Profile */}
                    {instance?.channel_type === 'whatsapp' && (instance?.profile_name || instance?.owner_jid) && (
                      <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                        <Avatar className="h-16 w-16">
                          <AvatarImage src={instance?.profile_pic_url || undefined} />
                          <AvatarFallback>
                            <User className="h-8 w-8" />
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium">{instance?.profile_name || 'Unknown'}</p>
                          <p className="text-sm text-muted-foreground">{instance?.owner_jid?.replace('@s.whatsapp.net', '')}</p>
                        </div>
                      </div>
                    )}

                    {/* QR Code (WhatsApp disconnected) */}
                    {instance?.channel_type === 'whatsapp' && !isConnected && (
                      <div className="space-y-4">
                        <Button variant="outline" onClick={() => setShowQR(!showQR)}>
                          <QrCode className="h-4 w-4 mr-2" />
                          {showQR ? 'Hide QR Code' : 'Show QR Code'}
                        </Button>
                        {showQR && (
                          <div className="flex justify-center p-4 bg-white rounded-lg">
                            {qrLoading ? (
                              <Loader2 className="h-8 w-8 animate-spin" />
                            ) : qrData?.qrcode ? (
                              <img src={qrData.qrcode} alt="QR Code" className="max-w-[256px]" />
                            ) : (
                              <p className="text-muted-foreground">QR code not available</p>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3">
                      <Button
                        variant="outline"
                        onClick={() => restartMutation.mutate()}
                        disabled={restartMutation.isPending}
                      >
                        {restartMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                        Restart
                      </Button>
                      {isConnected && (
                        <Button
                          variant="outline"
                          className="text-destructive"
                          onClick={() => logoutMutation.mutate()}
                          disabled={logoutMutation.isPending}
                        >
                          {logoutMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <LogOut className="h-4 w-4 mr-2" />}
                          Logout
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Agent Tab */}
              <TabsContent value="agent" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Bot className="h-5 w-5" />
                      Agent Configuration
                    </CardTitle>
                    <CardDescription>Configure the AI agent that handles incoming messages</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Provider Selection */}
                    {providers && providers.length > 0 && (
                      <div className="space-y-2">
                        <Label>Agent Provider</Label>
                        <Select
                          value={agentForm.agent_provider_id?.toString() || 'manual'}
                          onValueChange={(val) => {
                            if (val === 'manual') {
                              updateAgentForm('agent_provider_id', null);
                            } else {
                              updateAgentForm('agent_provider_id', parseInt(val));
                              // Auto-fill from provider
                              const provider = providers.find((p) => p.id === parseInt(val));
                              if (provider) {
                                updateAgentForm('agent_api_url', provider.api_url);
                              }
                            }
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider or configure manually" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="manual">Configure Manually</SelectItem>
                            {providers.map((provider) => (
                              <SelectItem key={provider.id} value={provider.id.toString()}>
                                {provider.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">Use shared credentials from a provider or configure manually</p>
                      </div>
                    )}

                    <Separator />

                    {/* API URL */}
                    <div className="space-y-2">
                      <Label htmlFor="agent_api_url">API URL</Label>
                      <Input
                        id="agent_api_url"
                        type="url"
                        placeholder="https://api.hive.example.com"
                        value={agentForm.agent_api_url}
                        onChange={(e) => updateAgentForm('agent_api_url', e.target.value)}
                        disabled={!!agentForm.agent_provider_id}
                      />
                    </div>

                    {/* API Key */}
                    <div className="space-y-2">
                      <Label htmlFor="agent_api_key">API Key</Label>
                      <Input
                        id="agent_api_key"
                        type="password"
                        placeholder={instance?.agent_api_key ? '••••••••' : 'Enter API key'}
                        value={agentForm.agent_api_key}
                        onChange={(e) => updateAgentForm('agent_api_key', e.target.value)}
                        disabled={!!agentForm.agent_provider_id}
                      />
                      <p className="text-xs text-muted-foreground">Leave empty to keep current key</p>
                    </div>

                    {/* Agent ID */}
                    <div className="space-y-2">
                      <Label htmlFor="agent_id">Agent ID</Label>
                      <Input
                        id="agent_id"
                        placeholder="agent-uuid or team-uuid"
                        value={agentForm.agent_id}
                        onChange={(e) => updateAgentForm('agent_id', e.target.value)}
                      />
                    </div>

                    {/* Agent Type */}
                    <div className="space-y-2">
                      <Label>Agent Type</Label>
                      <Select value={agentForm.agent_type} onValueChange={(val) => updateAgentForm('agent_type', val)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="agent">Agent</SelectItem>
                          <SelectItem value="team">Team</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <Separator />

                    {/* Timeout */}
                    <div className="space-y-2">
                      <Label htmlFor="agent_timeout">Response Timeout (seconds)</Label>
                      <Input
                        id="agent_timeout"
                        type="number"
                        min={10}
                        max={300}
                        value={agentForm.agent_timeout}
                        onChange={(e) => updateAgentForm('agent_timeout', parseInt(e.target.value) || 60)}
                        className="w-32"
                      />
                    </div>

                    {/* Stream Mode */}
                    <div className="flex items-center justify-between">
                      <div>
                        <Label htmlFor="stream_mode">Streaming Responses</Label>
                        <p className="text-xs text-muted-foreground">Enable real-time streaming of agent responses</p>
                      </div>
                      <Switch
                        id="stream_mode"
                        checked={agentForm.agent_stream_mode}
                        onCheckedChange={(checked) => updateAgentForm('agent_stream_mode', checked)}
                      />
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Messages Tab */}
              <TabsContent value="messages" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MessageSquare className="h-5 w-5" />
                      Message Handling
                    </CardTitle>
                    <CardDescription>Configure how messages are processed before sending to the agent</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Message Debounce */}
                    <div className="space-y-4 p-4 border rounded-lg">
                      <div className="flex items-start gap-3">
                        <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
                        <div className="flex-1 space-y-4">
                          <div>
                            <Label>Message Debounce</Label>
                            <p className="text-sm text-muted-foreground">
                              Wait before sending messages to the agent to collect multiple rapid messages.
                            </p>
                          </div>

                          <div className="space-y-2">
                            <Label htmlFor="debounce_mode">Mode</Label>
                            <Select
                              value={messagesForm.message_debounce_mode}
                              onValueChange={(val: 'disabled' | 'fixed' | 'randomized') => {
                                updateMessagesForm('message_debounce_mode', val);
                              }}
                            >
                              <SelectTrigger className="w-48">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="disabled">Disabled (instant)</SelectItem>
                                <SelectItem value="fixed">Fixed delay</SelectItem>
                                <SelectItem value="randomized">Randomized delay</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          {messagesForm.message_debounce_mode === 'fixed' && (
                            <div className="pl-4 border-l-2 space-y-3">
                              <Label>Delay (seconds): {messagesForm.message_debounce_seconds}s</Label>
                              <div className="flex items-center gap-4">
                                <Slider
                                  value={[messagesForm.message_debounce_seconds]}
                                  onValueChange={([val]) => updateMessagesForm('message_debounce_seconds', val)}
                                  min={1}
                                  max={600}
                                  step={1}
                                  className="flex-1"
                                />
                                <Input
                                  type="number"
                                  min={1}
                                  max={600}
                                  value={messagesForm.message_debounce_seconds}
                                  onChange={(e) => updateMessagesForm('message_debounce_seconds', Math.min(600, Math.max(1, parseInt(e.target.value) || 1)))}
                                  className="w-20"
                                />
                              </div>
                            </div>
                          )}

                          {messagesForm.message_debounce_mode === 'randomized' && (
                            <div className="pl-4 border-l-2 space-y-4">
                              <div className="space-y-3">
                                <Label>Min delay: {(messagesForm.message_debounce_min_ms / 1000).toFixed(1)}s ({messagesForm.message_debounce_min_ms}ms)</Label>
                                <div className="flex items-center gap-4">
                                  <Slider
                                    value={[messagesForm.message_debounce_min_ms]}
                                    onValueChange={([val]) => updateMessagesForm('message_debounce_min_ms', val)}
                                    min={0}
                                    max={600000}
                                    step={100}
                                    className="flex-1"
                                  />
                                  <Input
                                    type="number"
                                    min={0}
                                    max={600000}
                                    value={messagesForm.message_debounce_min_ms}
                                    onChange={(e) => updateMessagesForm('message_debounce_min_ms', Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)))}
                                    className="w-24"
                                  />
                                </div>
                              </div>
                              <div className="space-y-3">
                                <Label>Max delay: {(messagesForm.message_debounce_max_ms / 1000).toFixed(1)}s ({messagesForm.message_debounce_max_ms}ms)</Label>
                                <div className="flex items-center gap-4">
                                  <Slider
                                    value={[messagesForm.message_debounce_max_ms]}
                                    onValueChange={([val]) => updateMessagesForm('message_debounce_max_ms', val)}
                                    min={0}
                                    max={600000}
                                    step={100}
                                    className="flex-1"
                                  />
                                  <Input
                                    type="number"
                                    min={0}
                                    max={600000}
                                    value={messagesForm.message_debounce_max_ms}
                                    onChange={(e) => updateMessagesForm('message_debounce_max_ms', Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)))}
                                    className="w-24"
                                  />
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Auto Split */}
                    <div className="space-y-4 p-4 border rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <SplitSquareVertical className="h-5 w-5 text-muted-foreground mt-0.5" />
                          <div>
                            <Label htmlFor="auto_split">Auto-split Long Messages</Label>
                            <p className="text-sm text-muted-foreground">
                              Automatically split agent responses on double newlines (\\n\\n)
                            </p>
                          </div>
                        </div>
                        <Switch
                          id="auto_split"
                          checked={messagesForm.enable_auto_split}
                          onCheckedChange={(checked) => updateMessagesForm('enable_auto_split', checked)}
                        />
                      </div>

                      {/* Split Message Delay */}
                      {messagesForm.enable_auto_split && (
                        <div className="mt-4 pl-8 space-y-4 border-l-2 ml-2">
                          <div>
                            <Label className="text-sm">Delay Between Split Messages</Label>
                            <p className="text-xs text-muted-foreground">
                              Time to wait between sending each split message part (for human-like pacing)
                            </p>
                          </div>

                          <div className="space-y-2">
                            <Label htmlFor="split_mode">Mode</Label>
                            <Select
                              value={messagesForm.message_split_delay_mode}
                              onValueChange={(val: 'disabled' | 'fixed' | 'randomized') => {
                                updateMessagesForm('message_split_delay_mode', val);
                              }}
                            >
                              <SelectTrigger className="w-48">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="disabled">Disabled (instant)</SelectItem>
                                <SelectItem value="fixed">Fixed delay</SelectItem>
                                <SelectItem value="randomized">Randomized (human-like)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          {messagesForm.message_split_delay_mode === 'fixed' && (
                            <div className="space-y-3">
                              <Label>Delay: {(messagesForm.message_split_delay_fixed_ms / 1000).toFixed(1)}s ({messagesForm.message_split_delay_fixed_ms}ms)</Label>
                              <div className="flex items-center gap-4">
                                <Slider
                                  value={[messagesForm.message_split_delay_fixed_ms]}
                                  onValueChange={([val]) => updateMessagesForm('message_split_delay_fixed_ms', val)}
                                  min={0}
                                  max={600000}
                                  step={100}
                                  className="flex-1"
                                />
                                <Input
                                  type="number"
                                  min={0}
                                  max={600000}
                                  value={messagesForm.message_split_delay_fixed_ms}
                                  onChange={(e) => updateMessagesForm('message_split_delay_fixed_ms', Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)))}
                                  className="w-24"
                                />
                              </div>
                            </div>
                          )}

                          {messagesForm.message_split_delay_mode === 'randomized' && (
                            <div className="space-y-4">
                              <div className="space-y-3">
                                <Label>Min delay: {(messagesForm.message_split_delay_min_ms / 1000).toFixed(1)}s ({messagesForm.message_split_delay_min_ms}ms)</Label>
                                <div className="flex items-center gap-4">
                                  <Slider
                                    value={[messagesForm.message_split_delay_min_ms]}
                                    onValueChange={([val]) => updateMessagesForm('message_split_delay_min_ms', val)}
                                    min={0}
                                    max={600000}
                                    step={100}
                                    className="flex-1"
                                  />
                                  <Input
                                    type="number"
                                    min={0}
                                    max={600000}
                                    value={messagesForm.message_split_delay_min_ms}
                                    onChange={(e) => updateMessagesForm('message_split_delay_min_ms', Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)))}
                                    className="w-24"
                                  />
                                </div>
                              </div>
                              <div className="space-y-3">
                                <Label>Max delay: {(messagesForm.message_split_delay_max_ms / 1000).toFixed(1)}s ({messagesForm.message_split_delay_max_ms}ms)</Label>
                                <div className="flex items-center gap-4">
                                  <Slider
                                    value={[messagesForm.message_split_delay_max_ms]}
                                    onValueChange={([val]) => updateMessagesForm('message_split_delay_max_ms', val)}
                                    min={0}
                                    max={600000}
                                    step={100}
                                    className="flex-1"
                                  />
                                  <Input
                                    type="number"
                                    min={0}
                                    max={600000}
                                    value={messagesForm.message_split_delay_max_ms}
                                    onChange={(e) => updateMessagesForm('message_split_delay_max_ms', Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)))}
                                    className="w-24"
                                  />
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Username Prefix */}
                    <div className="space-y-4 p-4 border rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <User className="h-5 w-5 text-muted-foreground mt-0.5" />
                          <div>
                            <Label htmlFor="username_prefix">Disable Username Prefix</Label>
                            <p className="text-sm text-muted-foreground">
                              Don't prepend [username]: to messages sent to the agent.
                              Enable this if your agent handles user identification differently.
                            </p>
                          </div>
                        </div>
                        <Switch
                          id="username_prefix"
                          checked={messagesForm.disable_username_prefix}
                          onCheckedChange={(checked) => updateMessagesForm('disable_username_prefix', checked)}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Behavior Tab (WhatsApp only - Evolution API settings) */}
              {instance?.channel_type === 'whatsapp' && (
                <TabsContent value="behavior" className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Settings className="h-5 w-5" />
                        WhatsApp Behavior
                      </CardTitle>
                      <CardDescription>Configure WhatsApp-specific behavior and automation settings</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {settingsLoading ? (
                        <div className="flex justify-center py-8">
                          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                      ) : (
                        <>
                          {/* Call Settings */}
                          <div className="space-y-4 p-4 border rounded-lg">
                            <div className="flex items-start gap-3">
                              <Phone className="h-5 w-5 text-muted-foreground mt-0.5" />
                              <div className="flex-1 space-y-3">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <Label htmlFor="rejectCall">Auto-reject incoming calls</Label>
                                    <p className="text-sm text-muted-foreground">Automatically reject all incoming calls</p>
                                  </div>
                                  <Switch
                                    id="rejectCall"
                                    checked={behaviorForm.rejectCall}
                                    onCheckedChange={(checked) => updateBehaviorForm('rejectCall', checked)}
                                  />
                                </div>
                                {behaviorForm.rejectCall && (
                                  <div className="pl-4 border-l-2 space-y-2">
                                    <Label htmlFor="msgCall" className="text-xs text-muted-foreground">
                                      Rejection message
                                    </Label>
                                    <Input
                                      id="msgCall"
                                      placeholder="Sorry, I can't take calls right now"
                                      value={behaviorForm.msgCall}
                                      onChange={(e) => updateBehaviorForm('msgCall', e.target.value)}
                                      className="h-9"
                                    />
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Presence Settings */}
                          <div className="space-y-4 p-4 border rounded-lg">
                            <div className="flex items-center justify-between">
                              <div className="flex items-start gap-3">
                                <Eye className="h-5 w-5 text-muted-foreground mt-0.5" />
                                <div>
                                  <Label htmlFor="alwaysOnline">Always show as online</Label>
                                  <p className="text-sm text-muted-foreground">Keep your status as "online" at all times</p>
                                </div>
                              </div>
                              <Switch
                                id="alwaysOnline"
                                checked={behaviorForm.alwaysOnline}
                                onCheckedChange={(checked) => updateBehaviorForm('alwaysOnline', checked)}
                              />
                            </div>
                          </div>

                          {/* Message Settings */}
                          <div className="space-y-4 p-4 border rounded-lg">
                            <div className="flex items-start gap-3">
                              <MessageSquare className="h-5 w-5 text-muted-foreground mt-0.5" />
                              <div className="flex-1 space-y-4">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <Label htmlFor="readMessages">Auto-read messages</Label>
                                    <p className="text-sm text-muted-foreground">Automatically mark messages as read</p>
                                  </div>
                                  <Switch
                                    id="readMessages"
                                    checked={behaviorForm.readMessages}
                                    onCheckedChange={(checked) => updateBehaviorForm('readMessages', checked)}
                                  />
                                </div>
                                <Separator />
                                <div className="flex items-center justify-between">
                                  <div>
                                    <Label htmlFor="readStatus">Auto-read status updates</Label>
                                    <p className="text-sm text-muted-foreground">Automatically view status/stories from contacts</p>
                                  </div>
                                  <Switch
                                    id="readStatus"
                                    checked={behaviorForm.readStatus}
                                    onCheckedChange={(checked) => updateBehaviorForm('readStatus', checked)}
                                  />
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Group Settings */}
                          <div className="space-y-4 p-4 border rounded-lg">
                            <div className="flex items-center justify-between">
                              <div className="flex items-start gap-3">
                                <Users className="h-5 w-5 text-muted-foreground mt-0.5" />
                                <div>
                                  <Label htmlFor="groupsIgnore">Ignore group messages</Label>
                                  <p className="text-sm text-muted-foreground">Don't process messages from group chats</p>
                                </div>
                              </div>
                              <Switch
                                id="groupsIgnore"
                                checked={behaviorForm.groupsIgnore}
                                onCheckedChange={(checked) => updateBehaviorForm('groupsIgnore', checked)}
                              />
                            </div>
                          </div>

                          {/* Sync Settings */}
                          <div className="space-y-4 p-4 border rounded-lg">
                            <div className="flex items-center justify-between">
                              <div className="flex items-start gap-3">
                                <History className="h-5 w-5 text-muted-foreground mt-0.5" />
                                <div>
                                  <Label htmlFor="syncFullHistory">Sync full message history</Label>
                                  <p className="text-sm text-muted-foreground">Download complete message history on connection</p>
                                </div>
                              </div>
                              <Switch
                                id="syncFullHistory"
                                checked={behaviorForm.syncFullHistory}
                                onCheckedChange={(checked) => updateBehaviorForm('syncFullHistory', checked)}
                              />
                            </div>
                          </div>

                          {/* Save Button */}
                          {behaviorHasChanges && (
                            <Button
                              className="w-full"
                              onClick={() => saveBehaviorMutation.mutate(behaviorForm)}
                              disabled={saveBehaviorMutation.isPending}
                            >
                              {saveBehaviorMutation.isPending ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              ) : (
                                <Save className="h-4 w-4 mr-2" />
                              )}
                              Save Behavior Settings
                            </Button>
                          )}
                        </>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              )}

              {/* Webhooks Tab (WhatsApp only) */}
              {instance?.channel_type === 'whatsapp' && (
                <TabsContent value="webhooks" className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Webhook className="h-5 w-5" />
                        Webhook Configuration
                      </CardTitle>
                      <CardDescription>Configure webhooks, WebSocket, and RabbitMQ integrations</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-muted-foreground">
                        Webhook configuration is managed through the Evolution API settings.
                        Use the sidebar to access individual webhook configurations.
                      </p>
                      {/* TODO: Could inline webhook config here in future */}
                    </CardContent>
                  </Card>
                </TabsContent>
              )}
            </Tabs>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
