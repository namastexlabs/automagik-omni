import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Webhook, Loader2, Save } from 'lucide-react';
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
import { EventSelector } from '@/components/instance/EventSelector';
import { api } from '@/lib/api';

interface WebhookSheetProps {
  instanceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface WebhookForm {
  enabled: boolean;
  url: string;
  byEvents: boolean;
  base64: boolean;
  events: string[];
}

const defaultForm: WebhookForm = {
  enabled: false,
  url: '',
  byEvents: false,
  base64: false,
  events: [],
};

export function WebhookSheet({ instanceName, open, onOpenChange }: WebhookSheetProps) {
  const [form, setForm] = useState<WebhookForm>(defaultForm);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: webhook, isLoading } = useQuery({
    queryKey: ['webhook', instanceName],
    queryFn: () => api.evolution.getWebhook(instanceName),
    enabled: open,
  });

  useEffect(() => {
    if (webhook) {
      setForm({
        enabled: webhook.enabled ?? false,
        url: webhook.url ?? '',
        byEvents: webhook.webhookByEvents ?? webhook.byEvents ?? false,
        base64: webhook.webhookBase64 ?? webhook.base64 ?? false,
        events: Array.isArray(webhook.events) ? webhook.events : [],
      });
      setHasChanges(false);
    }
  }, [webhook]);

  const saveMutation = useMutation({
    mutationFn: (data: WebhookForm) => api.evolution.setWebhook(instanceName, data),
    onSuccess: () => {
      toast.success('Webhook settings saved');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['webhook', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  const updateForm = <K extends keyof WebhookForm>(key: K, value: WebhookForm[K]) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Webhook className="h-5 w-5" />
            Webhook - {instanceName}
            {form.enabled && <Badge variant="secondary" className="bg-green-500/20 text-green-600">Active</Badge>}
          </SheetTitle>
          <SheetDescription>
            Configure webhook notifications for events
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
                {/* Enable Toggle */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                  <Label htmlFor="webhook-enabled" className="text-sm font-medium">
                    Enable Webhook
                  </Label>
                  <Switch
                    id="webhook-enabled"
                    checked={form.enabled}
                    onCheckedChange={(checked) => updateForm('enabled', checked)}
                  />
                </div>

                {form.enabled && (
                  <>
                    {/* URL */}
                    <div className="space-y-2">
                      <Label htmlFor="webhook-url" className="text-sm font-medium">
                        Webhook URL
                      </Label>
                      <Input
                        id="webhook-url"
                        type="url"
                        placeholder="https://your-server.com/webhook"
                        value={form.url}
                        onChange={(e) => updateForm('url', e.target.value)}
                      />
                    </div>

                    {/* Options */}
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Options</h3>
                      <div className="space-y-3 pl-4">
                        <div className="flex items-center justify-between">
                          <Label htmlFor="webhook-byEvents" className="text-sm">
                            Send by event type
                          </Label>
                          <Switch
                            id="webhook-byEvents"
                            checked={form.byEvents}
                            onCheckedChange={(checked) => updateForm('byEvents', checked)}
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <Label htmlFor="webhook-base64" className="text-sm">
                            Encode media as Base64
                          </Label>
                          <Switch
                            id="webhook-base64"
                            checked={form.base64}
                            onCheckedChange={(checked) => updateForm('base64', checked)}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Events */}
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Events ({form.events.length} selected)
                      </Label>
                      <div className="p-4 rounded-lg bg-muted/50">
                        <EventSelector
                          selectedEvents={form.events}
                          onChange={(events) => updateForm('events', events)}
                        />
                      </div>
                    </div>
                  </>
                )}

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
                    Save Webhook
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
