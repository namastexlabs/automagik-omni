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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { api } from '@/lib';
import type {
  InstanceConfig,
  InstanceUpdateRequest,
  AgentProvider,
  InstanceProfileUpdate,
  InstanceProfileUpdateResponse,
} from '@/lib';
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
  Layers,
  Pencil,
  X,
} from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
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
    process_media_on_blocked: true,
  });

  // Profile editing state
  const [profileEditing, setProfileEditing] = useState(false);
  const [profileForm, setProfileForm] = useState({
    // WhatsApp fields
    profile_name: '',
    profile_status: '',
    profile_picture_url: '',
    profile_picture_base64: '',
    profile_picture_preview: '', // For showing preview
    // Discord fields
    bot_username: '',
    bot_avatar_url: '',
    bot_avatar_base64: '',
    bot_avatar_preview: '', // For showing preview
    activity_type: '' as '' | 'playing' | 'watching' | 'listening' | 'competing',
    activity_name: '',
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
        process_media_on_blocked: instance.process_media_on_blocked ?? true,
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

  const updateProfileMutation = useMutation({
    mutationFn: (data: InstanceProfileUpdate) =>
      api.instances.updateProfile(instanceName!, data) as Promise<InstanceProfileUpdateResponse>,
    onSuccess: (result) => {
      if (result.updated.length > 0) {
        toast.success(`Profile updated: ${result.updated.join(', ')}`);
      }
      if (result.errors.length > 0) {
        result.errors.forEach((error) => toast.error(error));
      }
      setProfileEditing(false);
      queryClient.invalidateQueries({ queryKey: ['connection-state', instanceName] });
      queryClient.invalidateQueries({ queryKey: ['instance', instanceName] });
    },
    onError: (err: Error) => toast.error(err.message || 'Failed to update profile'),
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

  const updateProfileForm = <K extends keyof typeof profileForm>(key: K, value: (typeof profileForm)[K]) => {
    setProfileForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleProfileImageUpload = (file: File, type: 'whatsapp' | 'discord') => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target?.result as string;
      if (type === 'whatsapp') {
        setProfileForm((prev) => ({
          ...prev,
          profile_picture_base64: base64,
          profile_picture_preview: base64,
          profile_picture_url: '', // Clear URL when file is uploaded
        }));
      } else {
        setProfileForm((prev) => ({
          ...prev,
          bot_avatar_base64: base64,
          bot_avatar_preview: base64,
          bot_avatar_url: '', // Clear URL when file is uploaded
        }));
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = () => {
    const data: InstanceProfileUpdate = {};

    if (instance?.channel_type === 'whatsapp') {
      if (profileForm.profile_name.trim()) data.profile_name = profileForm.profile_name.trim();
      if (profileForm.profile_status.trim()) data.profile_status = profileForm.profile_status.trim();
      // Use base64 if available, otherwise URL
      if (profileForm.profile_picture_base64) {
        data.profile_picture_base64 = profileForm.profile_picture_base64;
      } else if (profileForm.profile_picture_url.trim()) {
        data.profile_picture_url = profileForm.profile_picture_url.trim();
      }
    } else if (instance?.channel_type === 'discord') {
      if (profileForm.bot_username.trim()) data.bot_username = profileForm.bot_username.trim();
      // Use base64 if available, otherwise URL
      if (profileForm.bot_avatar_base64) {
        data.bot_avatar_base64 = profileForm.bot_avatar_base64;
      } else if (profileForm.bot_avatar_url.trim()) {
        data.bot_avatar_url = profileForm.bot_avatar_url.trim();
      }
      if (profileForm.activity_type) data.activity_type = profileForm.activity_type;
      if (profileForm.activity_name.trim()) data.activity_name = profileForm.activity_name.trim();
    }

    if (Object.keys(data).length === 0) {
      toast.error('No changes to save');
      return;
    }

    updateProfileMutation.mutate(data);
  };

  const startProfileEditing = () => {
    // Initialize form with current values
    if (instance?.channel_type === 'whatsapp') {
      setProfileForm({
        profile_name: instance.profile_name || '',
        profile_status: '',
        profile_picture_url: '',
        profile_picture_base64: '',
        profile_picture_preview: '',
        bot_username: '',
        bot_avatar_url: '',
        bot_avatar_base64: '',
        bot_avatar_preview: '',
        activity_type: '',
        activity_name: '',
      });
    } else if (instance?.channel_type === 'discord' && connectionState?.channel_data?.bot) {
      setProfileForm({
        profile_name: '',
        profile_status: '',
        profile_picture_url: '',
        profile_picture_base64: '',
        profile_picture_preview: '',
        bot_username: connectionState.channel_data.bot.name || '',
        bot_avatar_url: '',
        bot_avatar_base64: '',
        bot_avatar_preview: '',
        activity_type: '',
        activity_name: '',
      });
    }
    setProfileEditing(true);
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
      process_media_on_blocked: messagesForm.process_media_on_blocked,
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
                {saveMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
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
              <TabsList
                className={`grid w-full ${instance?.channel_type === 'whatsapp' ? 'grid-cols-5 max-w-3xl' : 'grid-cols-3 max-w-xl'}`}
              >
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
                      {isConnected ? (
                        <Wifi className="h-5 w-5 text-green-500" />
                      ) : (
                        <WifiOff className="h-5 w-5 text-red-500" />
                      )}
                      Connection Status
                    </CardTitle>
                    <CardDescription>
                      {instance?.channel_type === 'discord'
                        ? 'Discord bot connection status'
                        : 'WhatsApp Web connection status'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* WhatsApp Profile */}
                    {instance?.channel_type === 'whatsapp' && (instance?.profile_name || instance?.owner_jid) && (
                      <div className="space-y-4">
                        <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                          <div className="relative group">
                            <Avatar className="h-16 w-16">
                              <AvatarImage src={instance?.profile_pic_url || undefined} />
                              <AvatarFallback>
                                <User className="h-8 w-8" />
                              </AvatarFallback>
                            </Avatar>
                            {isConnected && !profileEditing && (
                              <button
                                onClick={startProfileEditing}
                                className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <Pencil className="h-5 w-5 text-white" />
                              </button>
                            )}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{instance?.profile_name || 'Unknown'}</p>
                            <p className="text-sm text-muted-foreground">
                              {instance?.owner_jid?.replace('@s.whatsapp.net', '')}
                            </p>
                          </div>
                          {isConnected && !profileEditing && (
                            <Button variant="outline" size="sm" onClick={startProfileEditing}>
                              <Pencil className="h-4 w-4 mr-2" />
                              Edit Profile
                            </Button>
                          )}
                        </div>

                        {/* WhatsApp Profile Edit Form */}
                        {profileEditing && instance?.channel_type === 'whatsapp' && (
                          <div className="p-4 border rounded-lg space-y-4">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium">Edit Profile</h4>
                              <Button variant="ghost" size="sm" onClick={() => setProfileEditing(false)}>
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                            <div className="space-y-3">
                              <div className="space-y-2">
                                <Label htmlFor="wa-profile-name">Profile Name</Label>
                                <Input
                                  id="wa-profile-name"
                                  placeholder="Enter new profile name"
                                  value={profileForm.profile_name}
                                  onChange={(e) => updateProfileForm('profile_name', e.target.value)}
                                />
                              </div>
                              <div className="space-y-2">
                                <Label htmlFor="wa-profile-status">Status / Bio</Label>
                                <Textarea
                                  id="wa-profile-status"
                                  placeholder="Enter new status message"
                                  value={profileForm.profile_status}
                                  onChange={(e) => updateProfileForm('profile_status', e.target.value)}
                                  rows={3}
                                />
                              </div>
                              <div className="space-y-2">
                                <Label>Profile Picture</Label>
                                <div className="flex items-center gap-4">
                                  {profileForm.profile_picture_preview && (
                                    <Avatar className="h-12 w-12">
                                      <AvatarImage src={profileForm.profile_picture_preview} />
                                      <AvatarFallback>
                                        <User className="h-6 w-6" />
                                      </AvatarFallback>
                                    </Avatar>
                                  )}
                                  <div className="flex-1 space-y-2">
                                    <Input
                                      type="file"
                                      accept="image/*"
                                      onChange={(e) => {
                                        const file = e.target.files?.[0];
                                        if (file) handleProfileImageUpload(file, 'whatsapp');
                                      }}
                                    />
                                    <p className="text-xs text-muted-foreground">Or enter a URL:</p>
                                    <Input
                                      placeholder="https://example.com/image.jpg"
                                      value={profileForm.profile_picture_url}
                                      onChange={(e) => {
                                        updateProfileForm('profile_picture_url', e.target.value);
                                        updateProfileForm('profile_picture_base64', '');
                                        updateProfileForm('profile_picture_preview', '');
                                      }}
                                    />
                                  </div>
                                </div>
                              </div>
                            </div>
                            <div className="flex gap-2 pt-2">
                              <Button onClick={handleSaveProfile} disabled={updateProfileMutation.isPending}>
                                {updateProfileMutation.isPending ? (
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                  <Save className="h-4 w-4 mr-2" />
                                )}
                                Save Profile
                              </Button>
                              <Button variant="outline" onClick={() => setProfileEditing(false)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Discord Bot Profile */}
                    {instance?.channel_type === 'discord' && connectionState?.channel_data?.bot && (
                      <div className="space-y-4">
                        <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                          <div className="relative group">
                            <Avatar className="h-16 w-16">
                              <AvatarImage src={connectionState.channel_data.bot.avatar_url || undefined} />
                              <AvatarFallback>
                                <DiscordIcon className="h-8 w-8 text-[#5865F2]" />
                              </AvatarFallback>
                            </Avatar>
                            {!profileEditing && (
                              <button
                                onClick={startProfileEditing}
                                className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <Pencil className="h-5 w-5 text-white" />
                              </button>
                            )}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium text-lg">
                              {connectionState.channel_data.bot.display_name || connectionState.channel_data.bot.name}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              @{connectionState.channel_data.bot.name}
                              {connectionState.channel_data.bot.discriminator !== '0' &&
                                `#${connectionState.channel_data.bot.discriminator}`}
                            </p>
                            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                              <span>{connectionState.channel_data.guild_count || 0} servers</span>
                              <span>{connectionState.channel_data.user_count || 0} users</span>
                              {connectionState.channel_data.latency_ms && (
                                <span>{connectionState.channel_data.latency_ms}ms latency</span>
                              )}
                            </div>
                          </div>
                          {!profileEditing && (
                            <Button variant="outline" size="sm" onClick={startProfileEditing}>
                              <Pencil className="h-4 w-4 mr-2" />
                              Edit Profile
                            </Button>
                          )}
                        </div>

                        {/* Discord Profile Edit Form */}
                        {profileEditing && instance?.channel_type === 'discord' && (
                          <div className="p-4 border rounded-lg space-y-4">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium">Edit Bot Profile</h4>
                              <Button variant="ghost" size="sm" onClick={() => setProfileEditing(false)}>
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                            <div className="space-y-3">
                              <div className="space-y-2">
                                <Label htmlFor="discord-username">Bot Username</Label>
                                <Input
                                  id="discord-username"
                                  placeholder="Enter new bot username"
                                  value={profileForm.bot_username}
                                  onChange={(e) => updateProfileForm('bot_username', e.target.value)}
                                />
                                <p className="text-xs text-muted-foreground text-yellow-600">
                                  Discord limits username changes to 2 per hour
                                </p>
                              </div>
                              <div className="space-y-2">
                                <Label>Avatar</Label>
                                <div className="flex items-center gap-4">
                                  {profileForm.bot_avatar_preview && (
                                    <Avatar className="h-12 w-12">
                                      <AvatarImage src={profileForm.bot_avatar_preview} />
                                      <AvatarFallback>
                                        <DiscordIcon className="h-6 w-6 text-[#5865F2]" />
                                      </AvatarFallback>
                                    </Avatar>
                                  )}
                                  <div className="flex-1 space-y-2">
                                    <Input
                                      type="file"
                                      accept="image/*"
                                      onChange={(e) => {
                                        const file = e.target.files?.[0];
                                        if (file) handleProfileImageUpload(file, 'discord');
                                      }}
                                    />
                                    <p className="text-xs text-muted-foreground">Or enter a URL:</p>
                                    <Input
                                      placeholder="https://example.com/avatar.png"
                                      value={profileForm.bot_avatar_url}
                                      onChange={(e) => {
                                        updateProfileForm('bot_avatar_url', e.target.value);
                                        updateProfileForm('bot_avatar_base64', '');
                                        updateProfileForm('bot_avatar_preview', '');
                                      }}
                                    />
                                  </div>
                                </div>
                              </div>
                              <Separator />
                              <div className="space-y-2">
                                <Label>Bot Activity</Label>
                                <div className="grid grid-cols-2 gap-2">
                                  <div className="space-y-2">
                                    <Select
                                      value={profileForm.activity_type || 'none'}
                                      onValueChange={(val) =>
                                        updateProfileForm(
                                          'activity_type',
                                          val === 'none' ? '' : (val as typeof profileForm.activity_type),
                                        )
                                      }
                                    >
                                      <SelectTrigger>
                                        <SelectValue placeholder="Activity type" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="none">No Activity</SelectItem>
                                        <SelectItem value="playing">Playing</SelectItem>
                                        <SelectItem value="watching">Watching</SelectItem>
                                        <SelectItem value="listening">Listening to</SelectItem>
                                        <SelectItem value="competing">Competing in</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                  <Input
                                    placeholder="Activity name"
                                    value={profileForm.activity_name}
                                    onChange={(e) => updateProfileForm('activity_name', e.target.value)}
                                    disabled={!profileForm.activity_type}
                                  />
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  Set what the bot appears to be doing (e.g., "Playing Minecraft")
                                </p>
                              </div>
                            </div>
                            <div className="flex gap-2 pt-2">
                              <Button onClick={handleSaveProfile} disabled={updateProfileMutation.isPending}>
                                {updateProfileMutation.isPending ? (
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                  <Save className="h-4 w-4 mr-2" />
                                )}
                                Save Profile
                              </Button>
                              <Button variant="outline" onClick={() => setProfileEditing(false)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Connected Servers */}
                        {connectionState.channel_data.guilds && connectionState.channel_data.guilds.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-sm font-medium">Connected Servers</p>
                            <div className="grid gap-2">
                              {connectionState.channel_data.guilds.map(
                                (guild: { id: string; name: string; icon_url?: string; member_count?: number }) => (
                                  <div key={guild.id} className="flex items-center gap-3 p-2 bg-muted/30 rounded-lg">
                                    <Avatar className="h-8 w-8">
                                      <AvatarImage src={guild.icon_url || undefined} />
                                      <AvatarFallback className="text-xs">
                                        {guild.name.slice(0, 2).toUpperCase()}
                                      </AvatarFallback>
                                    </Avatar>
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm font-medium truncate">{guild.name}</p>
                                      <p className="text-xs text-muted-foreground">
                                        {guild.member_count?.toLocaleString() || 0} members
                                      </p>
                                    </div>
                                  </div>
                                ),
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Discord - Not Connected */}
                    {instance?.channel_type === 'discord' && !connectionState?.channel_data?.bot && (
                      <div className="p-4 bg-muted/50 rounded-lg text-center">
                        <DiscordIcon className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                        <p className="text-muted-foreground">
                          {connectionState?.status === 'connecting' ? 'Connecting to Discord...' : 'Bot not connected'}
                        </p>
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
                          className="text-destructive"
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
                        <p className="text-xs text-muted-foreground">
                          Use shared credentials from a provider or configure manually
                        </p>
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
                                  onChange={(e) =>
                                    updateMessagesForm(
                                      'message_debounce_seconds',
                                      Math.min(600, Math.max(1, parseInt(e.target.value) || 1)),
                                    )
                                  }
                                  className="w-20"
                                />
                              </div>
                            </div>
                          )}

                          {messagesForm.message_debounce_mode === 'randomized' && (
                            <div className="pl-4 border-l-2 space-y-4">
                              <div className="space-y-3">
                                <Label>
                                  Min delay: {(messagesForm.message_debounce_min_ms / 1000).toFixed(1)}s (
                                  {messagesForm.message_debounce_min_ms}ms)
                                </Label>
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
                                    onChange={(e) =>
                                      updateMessagesForm(
                                        'message_debounce_min_ms',
                                        Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)),
                                      )
                                    }
                                    className="w-24"
                                  />
                                </div>
                              </div>
                              <div className="space-y-3">
                                <Label>
                                  Max delay: {(messagesForm.message_debounce_max_ms / 1000).toFixed(1)}s (
                                  {messagesForm.message_debounce_max_ms}ms)
                                </Label>
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
                                    onChange={(e) =>
                                      updateMessagesForm(
                                        'message_debounce_max_ms',
                                        Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)),
                                      )
                                    }
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
                              <Label>
                                Delay: {(messagesForm.message_split_delay_fixed_ms / 1000).toFixed(1)}s (
                                {messagesForm.message_split_delay_fixed_ms}ms)
                              </Label>
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
                                  onChange={(e) =>
                                    updateMessagesForm(
                                      'message_split_delay_fixed_ms',
                                      Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)),
                                    )
                                  }
                                  className="w-24"
                                />
                              </div>
                            </div>
                          )}

                          {messagesForm.message_split_delay_mode === 'randomized' && (
                            <div className="space-y-4">
                              <div className="space-y-3">
                                <Label>
                                  Min delay: {(messagesForm.message_split_delay_min_ms / 1000).toFixed(1)}s (
                                  {messagesForm.message_split_delay_min_ms}ms)
                                </Label>
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
                                    onChange={(e) =>
                                      updateMessagesForm(
                                        'message_split_delay_min_ms',
                                        Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)),
                                      )
                                    }
                                    className="w-24"
                                  />
                                </div>
                              </div>
                              <div className="space-y-3">
                                <Label>
                                  Max delay: {(messagesForm.message_split_delay_max_ms / 1000).toFixed(1)}s (
                                  {messagesForm.message_split_delay_max_ms}ms)
                                </Label>
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
                                    onChange={(e) =>
                                      updateMessagesForm(
                                        'message_split_delay_max_ms',
                                        Math.min(600000, Math.max(0, parseInt(e.target.value) || 0)),
                                      )
                                    }
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
                              Don't prepend [username]: to messages sent to the agent. Enable this if your agent handles
                              user identification differently.
                            </p>
                          </div>
                        </div>
                        <Switch
                          id="username_prefix"
                          checked={messagesForm.disable_username_prefix}
                          onCheckedChange={(checked) => updateMessagesForm('disable_username_prefix', checked)}
                        />
                      </div>

                      {/* Media Processing on Blocked */}
                      <div className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-start gap-3">
                          <Layers className="h-5 w-5 text-muted-foreground mt-0.5" />
                          <div>
                            <Label htmlFor="process_media_on_blocked">Process Media When Blocked</Label>
                            <p className="text-sm text-muted-foreground">
                              Transcribe audio and describe images even when the sender is blocked by access rules.
                              Useful for passive media collection without agent responses.
                            </p>
                          </div>
                        </div>
                        <Switch
                          id="process_media_on_blocked"
                          checked={messagesForm.process_media_on_blocked}
                          onCheckedChange={(checked) => updateMessagesForm('process_media_on_blocked', checked)}
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
                                    <p className="text-sm text-muted-foreground">
                                      Automatically reject all incoming calls
                                    </p>
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
                                  <p className="text-sm text-muted-foreground">
                                    Keep your status as "online" at all times
                                  </p>
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
                                    <p className="text-sm text-muted-foreground">
                                      Automatically view status/stories from contacts
                                    </p>
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
                                  <p className="text-sm text-muted-foreground">
                                    Don't process messages from group chats
                                  </p>
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
                                  <p className="text-sm text-muted-foreground">
                                    Download complete message history on connection
                                  </p>
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
                        Webhook configuration is managed through the Evolution API settings. Use the sidebar to access
                        individual webhook configurations.
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
