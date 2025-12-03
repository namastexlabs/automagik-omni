import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bot, Loader2, Save, CheckCircle, XCircle, Mic, Terminal, Hash, Server } from 'lucide-react';
import { toast } from 'sonner';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib';

interface DiscordBotSettingsSheetProps {
  instanceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface DiscordSettingsForm {
  discord_voice_enabled: boolean;
  discord_slash_commands_enabled: boolean;
  discord_default_channel_id: string;
  discord_guild_id: string;
}

const defaultSettings: DiscordSettingsForm = {
  discord_voice_enabled: false,
  discord_slash_commands_enabled: true,
  discord_default_channel_id: '',
  discord_guild_id: '',
};

export function DiscordBotSettingsSheet({ instanceName, open, onOpenChange }: DiscordBotSettingsSheetProps) {
  const [form, setForm] = useState<DiscordSettingsForm>(defaultSettings);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  // Fetch instance details
  const { data: instance, isLoading } = useQuery({
    queryKey: ['instance', instanceName],
    queryFn: () => api.instances.get(instanceName),
    enabled: open,
  });

  // Populate form from instance data
  useEffect(() => {
    if (instance) {
      setForm({
        discord_voice_enabled: instance.discord_voice_enabled ?? false,
        discord_slash_commands_enabled: instance.discord_slash_commands_enabled ?? true,
        discord_default_channel_id: instance.discord_default_channel_id ?? '',
        discord_guild_id: instance.discord_guild_id ?? '',
      });
      setHasChanges(false);
    }
  }, [instance]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (data: DiscordSettingsForm) => api.instances.update(instanceName, data),
    onSuccess: () => {
      toast.success('Bot settings saved');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['instance', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  const updateForm = (key: keyof DiscordSettingsForm, value: boolean | string) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-[#5865F2]" />
            Bot Settings - {instanceName}
          </SheetTitle>
          <SheetDescription>
            Configure Discord bot features and behavior
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] mt-6">
          <div className="space-y-6 pr-4">
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {/* Bot Status */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Bot Status</h3>
                  <div className="space-y-3 pl-4">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">Bot Token</span>
                      </div>
                      {instance?.has_discord_bot_token ? (
                        <Badge variant="default" className="bg-green-500">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Configured
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          <XCircle className="h-3 w-3 mr-1" />
                          Not Set
                        </Badge>
                      )}
                    </div>

                    {instance?.discord_client_id && (
                      <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                        <span className="text-sm">Client ID</span>
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {instance.discord_client_id}
                        </code>
                      </div>
                    )}
                  </div>
                </div>

                {/* Feature Toggles */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Features</h3>
                  <div className="space-y-3 pl-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Terminal className="h-4 w-4 text-muted-foreground" />
                        <Label htmlFor="slashCommands" className="text-sm">
                          Slash Commands
                        </Label>
                      </div>
                      <Switch
                        id="slashCommands"
                        checked={form.discord_slash_commands_enabled}
                        onCheckedChange={(checked) => updateForm('discord_slash_commands_enabled', checked)}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground pl-6">
                      Enable /help, /ask, /config, /status commands
                    </p>

                    <div className="flex items-center justify-between mt-4">
                      <div className="flex items-center gap-2">
                        <Mic className="h-4 w-4 text-muted-foreground" />
                        <Label htmlFor="voiceEnabled" className="text-sm">
                          Voice Channels
                        </Label>
                      </div>
                      <Switch
                        id="voiceEnabled"
                        checked={form.discord_voice_enabled}
                        onCheckedChange={(checked) => updateForm('discord_voice_enabled', checked)}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground pl-6">
                      Enable /voice-join, /voice-leave and voice recording
                    </p>
                  </div>
                </div>

                {/* Channel Configuration */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Channel Configuration</h3>
                  <div className="space-y-4 pl-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Server className="h-4 w-4 text-muted-foreground" />
                        <Label htmlFor="guildId" className="text-sm">
                          Guild ID (Optional)
                        </Label>
                      </div>
                      <Input
                        id="guildId"
                        placeholder="123456789012345678"
                        value={form.discord_guild_id}
                        onChange={(e) => updateForm('discord_guild_id', e.target.value)}
                        className="h-9 font-mono text-sm"
                      />
                      <p className="text-xs text-muted-foreground">
                        Restrict bot to a specific server. Leave empty for all servers.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Hash className="h-4 w-4 text-muted-foreground" />
                        <Label htmlFor="defaultChannel" className="text-sm">
                          Default Channel ID (Optional)
                        </Label>
                      </div>
                      <Input
                        id="defaultChannel"
                        placeholder="123456789012345678"
                        value={form.discord_default_channel_id}
                        onChange={(e) => updateForm('discord_default_channel_id', e.target.value)}
                        className="h-9 font-mono text-sm"
                      />
                      <p className="text-xs text-muted-foreground">
                        Channel for bot-initiated messages. Leave empty to use first available.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Save Button */}
                {hasChanges && (
                  <Button
                    className="w-full"
                    onClick={() => saveMutation.mutate(form)}
                    disabled={saveMutation.isPending}
                  >
                    {saveMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    Save Bot Settings
                  </Button>
                )}
              </>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
