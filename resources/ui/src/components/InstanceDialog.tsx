import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { api } from '@/lib/api';
import { AlertCircle, Loader2 } from 'lucide-react';
import type { InstanceConfig, InstanceCreateRequest, InstanceUpdateRequest } from '@/lib/types';

interface InstanceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instance?: InstanceConfig | null;
  onInstanceCreated?: (instanceName: string, channelType: string) => void;
}

// Normalize instance name: remove spaces, convert to lowercase, replace with hyphens
function normalizeInstanceName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')  // Replace spaces with hyphens
    .replace(/[^a-z0-9-_]/g, '')  // Remove invalid characters
    .replace(/-+/g, '-')  // Collapse multiple hyphens
    .replace(/^-|-$/g, '');  // Remove leading/trailing hyphens
}

export function InstanceDialog({ open, onOpenChange, instance, onInstanceCreated }: InstanceDialogProps) {
  const queryClient = useQueryClient();
  const isEditing = !!instance;

  const [formData, setFormData] = useState({
    name: '',
    channel_type: 'whatsapp',
    // REQUIRED Agent fields
    agent_api_url: '',
    agent_api_key: '',
    // Optional fields
    default_agent: '',
    is_default: false,
    automagik_instance_name: '',
    // WhatsApp
    phone_number: '',
    // Discord
    discord_bot_token: '',
    discord_client_id: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [nameWarning, setNameWarning] = useState<string | null>(null);

  // Reset form when dialog opens/closes or instance changes
  useEffect(() => {
    if (open) {
      if (instance) {
        setFormData({
          name: instance.name,
          channel_type: instance.channel_type,
          agent_api_url: instance.agent_api_url || '',
          agent_api_key: instance.agent_api_key || '',
          default_agent: instance.default_agent || '',
          is_default: instance.is_default,
          automagik_instance_name: instance.automagik_instance_name || '',
          phone_number: instance.phone_number || '',
          discord_bot_token: '', // Never populate token for security
          discord_client_id: instance.discord_client_id || '',
        });
      } else {
        setFormData({
          name: '',
          channel_type: 'whatsapp',
          agent_api_url: '',
          agent_api_key: '',
          default_agent: '',
          is_default: false,
          automagik_instance_name: '',
          phone_number: '',
          discord_bot_token: '',
          discord_client_id: '',
        });
      }
      setError(null);
      setNameWarning(null);
    }
  }, [open, instance]);

  const createMutation = useMutation({
    mutationFn: (data: InstanceCreateRequest) => api.instances.create(data),
    onSuccess: (createdInstance) => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Instance "${createdInstance.name}" created successfully`);
      onOpenChange(false);
      // Notify parent to show QR code if WhatsApp
      if (onInstanceCreated && createdInstance.channel_type === 'whatsapp') {
        onInstanceCreated(createdInstance.name, createdInstance.channel_type);
      }
    },
    onError: (error: Error) => {
      setError(error.message);
      toast.error(`Failed to create instance: ${error.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: InstanceUpdateRequest }) =>
      api.instances.update(name, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Instance "${variables.name}" updated successfully`);
      onOpenChange(false);
    },
    onError: (error: Error, variables) => {
      setError(error.message);
      toast.error(`Failed to update instance "${variables.name}": ${error.message}`);
    },
  });

  const handleNameChange = (value: string) => {
    const normalized = normalizeInstanceName(value);
    setFormData({ ...formData, name: value });

    if (value !== normalized && value.length > 0) {
      setNameWarning(`Will be saved as: "${normalized}"`);
    } else {
      setNameWarning(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Normalize the name before submission
    const normalizedName = normalizeInstanceName(formData.name);

    if (!normalizedName) {
      setError('Instance name is required and must contain valid characters');
      return;
    }

    if (isEditing) {
      // Update existing instance
      const updateData: InstanceUpdateRequest = {
        is_default: formData.is_default,
        agent_api_url: formData.agent_api_url || undefined,
        agent_api_key: formData.agent_api_key || undefined,
        default_agent: formData.default_agent || null,
        automagik_instance_name: formData.automagik_instance_name || null,
      };

      if (formData.channel_type === 'whatsapp') {
        updateData.phone_number = formData.phone_number || null;
      } else if (formData.channel_type === 'discord') {
        if (formData.discord_bot_token) {
          updateData.discord_bot_token = formData.discord_bot_token;
        }
        updateData.discord_client_id = formData.discord_client_id || null;
      }

      updateMutation.mutate({ name: instance.name, data: updateData });
    } else {
      // Create new instance
      const createData: InstanceCreateRequest = {
        name: normalizedName,
        channel_type: formData.channel_type,
        agent_api_url: formData.agent_api_url,
        agent_api_key: formData.agent_api_key,
        default_agent: formData.default_agent || null,
        is_default: formData.is_default,
        automagik_instance_name: formData.automagik_instance_name || null,
      };

      if (formData.channel_type === 'whatsapp') {
        createData.phone_number = formData.phone_number || null;
        // Backend will handle Evolution API config automatically
      } else if (formData.channel_type === 'discord') {
        if (!formData.discord_bot_token) {
          setError('Discord bot token is required for Discord instances');
          return;
        }
        createData.discord_bot_token = formData.discord_bot_token;
        createData.discord_client_id = formData.discord_client_id || null;
      }

      createMutation.mutate(createData);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isEditing ? 'Edit Instance' : 'Create New Instance'}</DialogTitle>
            <DialogDescription>
              {isEditing
                ? 'Update the instance configuration'
                : 'Configure a new messaging channel instance'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Instance Name */}
            <div className="grid gap-2">
              <Label htmlFor="name">
                Instance Name *
                <span className="text-xs text-muted-foreground ml-2">
                  (lowercase, no spaces)
                </span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="my-whatsapp-instance"
                required
                disabled={isEditing || isPending}
              />
              {nameWarning && (
                <p className="text-xs text-warning">{nameWarning}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Unique identifier for this instance (letters, numbers, hyphens only)
              </p>
            </div>

            {/* Channel Type */}
            <div className="grid gap-2">
              <Label htmlFor="channel_type">Channel Type *</Label>
              <Select
                value={formData.channel_type}
                onValueChange={(value) => setFormData({ ...formData, channel_type: value })}
                disabled={isEditing || isPending}
              >
                <SelectTrigger id="channel_type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="discord">Discord</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Agent API URL */}
            <div className="grid gap-2">
              <Label htmlFor="agent_api_url">Agent API URL *</Label>
              <Input
                id="agent_api_url"
                type="url"
                value={formData.agent_api_url}
                onChange={(e) => setFormData({ ...formData, agent_api_url: e.target.value })}
                placeholder="http://localhost:8000"
                required
                disabled={isPending}
              />
              <p className="text-xs text-muted-foreground">
                Automagik agent API endpoint
              </p>
            </div>

            {/* Agent API Key */}
            <div className="grid gap-2">
              <Label htmlFor="agent_api_key">Agent API Key *</Label>
              <Input
                id="agent_api_key"
                type="password"
                value={formData.agent_api_key}
                onChange={(e) => setFormData({ ...formData, agent_api_key: e.target.value })}
                placeholder="••••••••"
                required
                disabled={isPending}
              />
            </div>

            {/* Default Agent */}
            <div className="grid gap-2">
              <Label htmlFor="default_agent">Default Agent (Optional)</Label>
              <Input
                id="default_agent"
                value={formData.default_agent}
                onChange={(e) => setFormData({ ...formData, default_agent: e.target.value })}
                placeholder="agent-name"
                disabled={isPending}
              />
              <p className="text-xs text-muted-foreground">
                Default agent to use for this instance
              </p>
            </div>

            {/* Automagik Instance Name */}
            <div className="grid gap-2">
              <Label htmlFor="automagik_instance_name">Automagik Instance Name (Optional)</Label>
              <Input
                id="automagik_instance_name"
                value={formData.automagik_instance_name}
                onChange={(e) => setFormData({ ...formData, automagik_instance_name: e.target.value })}
                placeholder="my-agent-instance"
                disabled={isPending}
              />
            </div>

            {/* WhatsApp Fields */}
            {formData.channel_type === 'whatsapp' && (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="phone_number">Phone Number (Optional)</Label>
                  <Input
                    id="phone_number"
                    value={formData.phone_number}
                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                    placeholder="+1234567890"
                    disabled={isPending}
                  />
                  <p className="text-xs text-muted-foreground">
                    Phone number for display purposes
                  </p>
                </div>
                <Alert>
                  <AlertDescription className="text-xs">
                    ℹ️ Evolution API configuration is handled automatically by the backend
                  </AlertDescription>
                </Alert>
              </>
            )}

            {/* Discord Fields */}
            {formData.channel_type === 'discord' && (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="discord_bot_token">Discord Bot Token *</Label>
                  <Input
                    id="discord_bot_token"
                    type="password"
                    value={formData.discord_bot_token}
                    onChange={(e) => setFormData({ ...formData, discord_bot_token: e.target.value })}
                    placeholder="••••••••"
                    required={!isEditing}
                    disabled={isPending}
                  />
                  {isEditing && (
                    <p className="text-xs text-warning">
                      Leave empty to keep existing token
                    </p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="discord_client_id">Discord Client ID (Optional)</Label>
                  <Input
                    id="discord_client_id"
                    value={formData.discord_client_id}
                    onChange={(e) => setFormData({ ...formData, discord_client_id: e.target.value })}
                    placeholder="123456789012345678"
                    disabled={isPending}
                  />
                </div>
              </>
            )}

            {/* Set as Default */}
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                className="h-4 w-4 rounded border-border"
                disabled={isPending}
              />
              <Label htmlFor="is_default" className="cursor-pointer">
                Set as default instance
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" className="gradient-primary" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {isEditing ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>{isEditing ? 'Update Instance' : 'Create Instance'}</>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
