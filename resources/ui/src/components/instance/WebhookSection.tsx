import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Webhook, Loader2, Save, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { EventSelector } from './EventSelector';
import { api } from '@/lib';

interface WebhookSectionProps {
  instanceName: string;
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

export function WebhookSection({ instanceName }: WebhookSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [form, setForm] = useState<WebhookForm>(defaultForm);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: webhook, isLoading } = useQuery({
    queryKey: ['webhook', instanceName],
    queryFn: () => api.evolution.getWebhook(instanceName),
    enabled: isOpen,
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
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <CardHeader className="pb-3 cursor-pointer hover:bg-muted/50 rounded-t-lg">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Webhook className="h-4 w-4" />
                Webhook
                {form.enabled && <Badge variant="secondary" className="bg-green-500/20 text-green-600">Active</Badge>}
              </span>
              <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </CardTitle>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">
            {isLoading ? (
              <div className="flex justify-center py-4">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <>
                {/* Enable Toggle */}
                <div className="flex items-center justify-between">
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
                    <div className="space-y-1.5">
                      <Label htmlFor="webhook-url" className="text-xs text-muted-foreground">
                        Webhook URL
                      </Label>
                      <Input
                        id="webhook-url"
                        type="url"
                        placeholder="https://your-server.com/webhook"
                        value={form.url}
                        onChange={(e) => updateForm('url', e.target.value)}
                        className="h-8 text-sm"
                      />
                    </div>

                    {/* Options */}
                    <div className="space-y-2">
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

                    {/* Events */}
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">
                        Events ({form.events.length} selected)
                      </Label>
                      <EventSelector
                        selectedEvents={form.events}
                        onChange={(events) => updateForm('events', events)}
                      />
                    </div>
                  </>
                )}

                {/* Save Button */}
                {hasChanges && (
                  <Button
                    className="w-full"
                    size="sm"
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
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
