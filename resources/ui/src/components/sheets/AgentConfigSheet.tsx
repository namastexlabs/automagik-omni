import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bot, Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { api } from '@/lib';
import type { InstanceConfig, InstanceUpdateRequest } from '@/lib';

interface AgentConfigSheetProps {
  instanceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface AgentConfigForm {
  agent_api_url: string;
  agent_api_key: string;
  default_agent: string;
  agent_id: string;
  agent_type: string;
  agent_timeout: number;
  agent_stream_mode: boolean;
  enable_auto_split: boolean;
}

const defaultConfig: AgentConfigForm = {
  agent_api_url: '',
  agent_api_key: '',
  default_agent: '',
  agent_id: '',
  agent_type: '',
  agent_timeout: 60,
  agent_stream_mode: false,
  enable_auto_split: true,
};

export function AgentConfigSheet({ instanceName, open, onOpenChange }: AgentConfigSheetProps) {
  const [form, setForm] = useState<AgentConfigForm>(defaultConfig);
  const [hasChanges, setHasChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch instance data to get current config
  const { data: instances, isLoading } = useQuery<InstanceConfig[]>({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100 }),
    enabled: open,
  });

  const instance = instances?.find((i) => i.name === instanceName);

  useEffect(() => {
    if (instance) {
      setForm({
        agent_api_url: instance.agent_api_url || '',
        agent_api_key: '', // Don't show existing key
        default_agent: instance.default_agent || '',
        agent_id: instance.agent_id || '',
        agent_type: instance.agent_type || '',
        agent_timeout: instance.agent_timeout || 60,
        agent_stream_mode: instance.agent_stream_mode || false,
        enable_auto_split: instance.enable_auto_split ?? true,
      });
      setHasChanges(false);
      setError(null);
    }
  }, [instance]);

  const saveMutation = useMutation({
    mutationFn: (data: InstanceUpdateRequest) => api.instances.update(instanceName, data),
    onSuccess: () => {
      toast.success('Agent configuration saved');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to save configuration');
    },
  });

  const updateForm = <K extends keyof AgentConfigForm>(key: K, value: AgentConfigForm[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
    setError(null);
  };

  const handleSave = () => {
    const updateData: InstanceUpdateRequest = {
      agent_timeout: form.agent_timeout,
      agent_stream_mode: form.agent_stream_mode,
      enable_auto_split: form.enable_auto_split,
    };

    // Only include non-empty string fields
    if (form.agent_api_url.trim()) {
      updateData.agent_api_url = form.agent_api_url.trim();
    }
    if (form.agent_api_key.trim()) {
      updateData.agent_api_key = form.agent_api_key.trim();
    }
    if (form.default_agent.trim()) {
      updateData.default_agent = form.default_agent.trim();
    }
    if (form.agent_id.trim()) {
      updateData.agent_id = form.agent_id.trim();
    }
    if (form.agent_type.trim()) {
      updateData.agent_type = form.agent_type.trim();
    }

    saveMutation.mutate(updateData);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent Config - {instanceName}
          </SheetTitle>
          <SheetDescription>Configure Hive agent integration for this instance</SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] mt-6">
          <div className="space-y-6 pr-4">
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* API Configuration */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">API Configuration</h3>
                  <div className="space-y-3 pl-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="agent_api_url" className="text-sm">
                        Hive API URL
                      </Label>
                      <Input
                        id="agent_api_url"
                        type="url"
                        placeholder="https://api.hive.example.com"
                        value={form.agent_api_url}
                        onChange={(e) => updateForm('agent_api_url', e.target.value)}
                        className="h-9"
                      />
                      <p className="text-xs text-muted-foreground">The URL of your Hive agent API</p>
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="agent_api_key" className="text-sm">
                        Hive API Key
                      </Label>
                      <Input
                        id="agent_api_key"
                        type="password"
                        placeholder={instance?.agent_api_key ? '••••••••' : 'Enter API key'}
                        value={form.agent_api_key}
                        onChange={(e) => updateForm('agent_api_key', e.target.value)}
                        className="h-9"
                      />
                      <p className="text-xs text-muted-foreground">Leave empty to keep current key</p>
                    </div>
                  </div>
                </div>

                {/* Agent Identity */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Agent Identity</h3>
                  <div className="space-y-3 pl-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="default_agent" className="text-sm">
                        Default Agent Name
                      </Label>
                      <Input
                        id="default_agent"
                        placeholder="my-agent"
                        value={form.default_agent}
                        onChange={(e) => updateForm('default_agent', e.target.value)}
                        className="h-9"
                      />
                      <p className="text-xs text-muted-foreground">Agent name to use for incoming messages</p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="agent_id" className="text-sm">
                          Agent ID
                        </Label>
                        <Input
                          id="agent_id"
                          placeholder="agent-uuid"
                          value={form.agent_id}
                          onChange={(e) => updateForm('agent_id', e.target.value)}
                          className="h-9"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label htmlFor="agent_type" className="text-sm">
                          Agent Type
                        </Label>
                        <Input
                          id="agent_type"
                          placeholder="e.g., assistant"
                          value={form.agent_type}
                          onChange={(e) => updateForm('agent_type', e.target.value)}
                          className="h-9"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Response Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Response Settings</h3>
                  <div className="space-y-3 pl-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="agent_timeout" className="text-sm">
                        Response Timeout (seconds)
                      </Label>
                      <Input
                        id="agent_timeout"
                        type="number"
                        min={10}
                        max={300}
                        value={form.agent_timeout}
                        onChange={(e) => updateForm('agent_timeout', parseInt(e.target.value) || 60)}
                        className="h-9 w-32"
                      />
                      <p className="text-xs text-muted-foreground">Max time to wait for agent response (10-300s)</p>
                    </div>

                    <div className="flex items-center justify-between">
                      <Label htmlFor="agent_stream_mode" className="text-sm">
                        Enable streaming responses
                      </Label>
                      <Switch
                        id="agent_stream_mode"
                        checked={form.agent_stream_mode}
                        onCheckedChange={(checked) => updateForm('agent_stream_mode', checked)}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <Label htmlFor="enable_auto_split" className="text-sm">
                        Auto-split long messages
                      </Label>
                      <Switch
                        id="enable_auto_split"
                        checked={form.enable_auto_split}
                        onCheckedChange={(checked) => updateForm('enable_auto_split', checked)}
                      />
                    </div>
                  </div>
                </div>

                {/* Save Button */}
                {hasChanges && (
                  <Button className="w-full" onClick={handleSave} disabled={saveMutation.isPending}>
                    {saveMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    Save Configuration
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
